import re
from pathlib import Path
from typing import Any
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, Template
from pinecone import Pinecone
from pinecone.db_data.index import Index
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.clients.graph_client import GraphClient
from app.clients.mongodb_client import DocumentStoreClient
from app.clients.redis_client import RedisClient
from app.db.models.choices import ChatModelProvider
from app.rag.types import NodeLabel
from app.settings import Settings

# Constants
TEMPLATE_DIRECTORY = Path(__file__).parent / "templates"


class TextContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    template: Template
    context_by_citation_number: dict[int, dict[str, str]] = Field(default_factory=dict)

    @property
    def context_str(self) -> str:
        return "\n".join(
            [
                self.template.render(v)
                for v in list(self.context_by_citation_number.values())
            ]
        )


class PersonContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    template: Template
    person_info: list[dict[str, str]]

    @property
    def context_str(self) -> str:
        return "\n".join([self.template.render(p) for p in self.person_info])


class QueryContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    template: Template
    detailed_user_query: str
    text_context: TextContext
    person_context: PersonContext

    @property
    def context_str(self) -> str:
        if self.text_context.context_by_citation_number:
            context_str = self.template.render(
                {
                    "context": self.text_context.context_str,
                    "people": self.person_context.context_str,
                }
            )
        else:
            context_str = ""
        return context_str


class RagAgent:
    namespace: str
    pc: Pinecone
    neo4j: GraphClient
    redis_client: RedisClient
    mongodb_client: DocumentStoreClient

    index: Index
    environment: Environment
    llm_agent: Agent

    def __init__(
        self,
        *,
        namespace: str,
        pc: Pinecone,
        neo4j: GraphClient,
        redis_client: RedisClient,
        mongodb_client: DocumentStoreClient,
        chat_model_provider: ChatModelProvider,
        model_name: str,
        api_key: str,
    ):
        self.namespace = namespace
        self.pc = pc
        self.neo4j = neo4j
        self.redis_client = redis_client
        self.mongodb_client = mongodb_client

        # Pinecone index
        self.index = self.pc.Index(host=Settings.PINECONE.INDEX_HOST)

        # Jinja2 environment
        self.environment = Environment(loader=FileSystemLoader(TEMPLATE_DIRECTORY))

        # Agent
        self.llm_agent = self.create_llm_agent(
            model_provider=chat_model_provider,
            model_name=model_name,
            api_key=api_key,
        )

    def create_llm_agent(
        self, model_provider: ChatModelProvider, model_name: str, api_key: str
    ) -> Agent:
        with open(Settings.TEMPLATES_ROOT / "main_system_prompt.txt", "r") as f:
            system_prompt = f.read()

        match model_provider:
            case ChatModelProvider.OPENAI:
                model = OpenAIModel(
                    model_name, provider=OpenAIProvider(api_key=api_key)
                )
            case ChatModelProvider.ANTHROPIC:
                model = AnthropicModel(
                    model_name, provider=AnthropicProvider(api_key=api_key)
                )
            case ChatModelProvider.GEMINI:
                model = GeminiModel(
                    model_name, provider=GoogleGLAProvider(api_key=api_key)
                )
            case ChatModelProvider.GROQ:
                model = GroqModel(model_name, provider=GroqProvider(api_key=api_key))
            case ChatModelProvider.MISTRAL:
                model = MistralModel(
                    model_name, provider=MistralProvider(api_key=api_key)
                )
            case _:
                raise Exception(f"Unsupported model type: {model_provider}")

        agent = Agent(
            model=model,
            system_prompt=system_prompt,
        )
        return agent

    def process_person_nodes(self, graph_data: list[dict[str, Any]]) -> PersonContext:
        template = self.environment.get_template("user_context.txt")
        person_info = []
        for node in graph_data:
            if NodeLabel.PERSON in node["n_labels"] and node["n"]["content"]:
                context_n = {
                    "name": node["n"]["content"],
                    "platform": node["n"]["source"],
                }
                person_info.append(template.render(context_n))

            if (
                node["m"]
                and node["m_labels"]
                and NodeLabel.PERSON in node["m_labels"]
                and node["m"]["content"]
            ):
                context_m = {
                    "name": node["m"]["content"],
                    "platform": node["m"]["source"],
                }
                person_info.append(template.render(context_m))

        return PersonContext(
            template=template,
            person_info=person_info,
        )

    @staticmethod
    def process_individual_text_node(
        text_node: dict[str, Any], node_key: str, citation_number: int
    ) -> dict[str, str]:
        text_node_context: dict[str, str] = {
            "citation_number": str(citation_number),
        }
        for k, v in text_node[node_key].items():
            text_node_context[k] = v
        return text_node_context

    def process_text_nodes(self, graph_data: list[dict[str, Any]]) -> TextContext:
        template = self.environment.get_template("text_context.txt")

        # Process nodes in the graph data. Be mindful of duplicate nodes
        citation_number = 1
        context_by_citation_number: dict[int, dict[str, str]] = {}
        for node in graph_data:
            # Process text content for the main node. This is the node whose ID matched
            # one of the vectors retrieved from Pinecone.
            if NodeLabel.TEXT in node["n_labels"]:
                context_by_citation_number[
                    citation_number
                ] = self.process_individual_text_node(node, "n", citation_number)
                citation_number += 1

            # Node n has an outbound relationship to node m. If node m is also a text
            # node, process the text.
            if node["m"] and node["m_labels"] and NodeLabel.TEXT in node["m_labels"]:
                context_by_citation_number[
                    citation_number
                ] = self.process_individual_text_node(node, "m", citation_number)
                citation_number += 1

            # Node n has an inbound relationship from node p. If node p is also a text
            # node, process the text.
            if node["p"] and node["p_labels"] and NodeLabel.TEXT in node["p_labels"]:
                context_by_citation_number[
                    citation_number
                ] = self.process_individual_text_node(node, "p", citation_number)
                citation_number += 1

        return TextContext(
            template=template, context_by_citation_number=context_by_citation_number
        )

    async def build_detailed_user_query(
        self, query: str, history: list[ModelMessage]
    ) -> str:
        if history:
            # We will create a user message that asks the LLM to create a more detailed
            # version of the user's original query.
            prompt_builder_template = self.environment.get_template(
                "prompt_builder.txt"
            )
            prompt_builder_query = prompt_builder_template.render(user_query=query)
            result = await self.llm_agent.run(
                user_prompt=prompt_builder_query, message_history=history
            )
            return result.data
        else:
            return query

    async def build_query_context(
        self, query: str, history: list[ModelMessage]
    ) -> QueryContext:
        detailed_user_query = await self.build_detailed_user_query(query, history)

        # Embed the query
        embeddings = self.pc.inference.embed(
            model=Settings.PINECONE.INDEX_MODEL,
            inputs=[detailed_user_query],
            parameters={"input_type": "passage", "truncate": "END"},
        )

        # Query Pinecone
        result = self.index.query(
            vector=embeddings.data[0]["values"],
            namespace=self.namespace,
            top_k=5,
            include_metadata=True,
        )
        similar_vectors = result["matches"]

        # Query graph db for related nodes. Keep track of ID order.
        id_order: dict[str, int] = {
            match["metadata"]["id"]: i for i, match in enumerate(similar_vectors)
        }
        node_id_set = list(id_order.keys())

        # Use two hops in order to retrieve data
        cypher = "\n".join(
            [
                "MATCH (n) WHERE n.id IN $ids ",
                "OPTIONAL MATCH (n)-[r*1..2]->(m) ",
                "OPTIONAL MATCH (p)-[r2:LINKED_TO|HAS*1..2]->(n) ",
                "RETURN n, labels(n) as n_labels, m, labels(m) as m_labels, p, labels(p) as p_labels",
            ]
        )
        graph_data = self.neo4j.execute_query(cypher_query=cypher, ids=node_id_set)

        # Sort to ensure that the order of graph IDs matches the order sent by Pinecone.
        # Then, process the Text and Person nodes.
        graph_data = sorted(
            graph_data, key=lambda x: id_order.get(x["n"]["id"], float("inf"))
        )
        text_context = self.process_text_nodes(graph_data)
        person_context = self.process_person_nodes(graph_data)

        return QueryContext(
            template=self.environment.get_template("full_context.txt"),
            detailed_user_query=detailed_user_query,
            text_context=text_context,
            person_context=person_context,
        )

    @staticmethod
    def parse_citations_from_response(response: str) -> list[int]:
        # All citations will be in superscript
        citation_matches = re.findall(pattern=r"\^([0-9,]+)\^", string=response)

        citations_with_duplicates: list[int] = []
        for cit in citation_matches:
            # In case there are multiple citations...
            for c in cit.split(","):
                citations_with_duplicates.append(int(c))

        # Remove duplicates, but maintain the same order
        seen = set()
        citations: list[int] = []
        for int_cit in citations_with_duplicates:
            if int_cit not in seen:
                seen.add(int_cit)
                citations.append(int_cit)

        return citations

    def get_chat_history(self, user_id: UUID, chat_id: UUID) -> list[ModelMessage]:
        messages = self.redis_client.retrieve_messages_from_redis(chat_id)
        if not messages:
            messages = self.mongodb_client.get_messages_from_chat(user_id, chat_id)
        history = ModelMessagesTypeAdapter.validate_python(messages)
        return history
