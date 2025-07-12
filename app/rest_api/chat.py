import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, WebSocket
from fastapi.exceptions import HTTPException
from kubernetes import config
from pinecone import Pinecone
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelRequest,
    SystemPromptPart,
    UserPromptPart,
)
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
from pydantic_ai.result import StreamedRunResult
from pydantic_core import to_jsonable_python
from starlette.status import (
    HTTP_202_ACCEPTED,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.clients.graph_client import GraphClient
from app.clients.k8s_client import KubernetesOperator
from app.clients.mongodb_client import Chat, Citation, DocumentStoreClient
from app.clients.redis_client import RedisClient
from app.db.container import Container
from app.db.models.auth import User
from app.db.models.choices import ChatModelProvider
from app.db.security import get_current_user
from app.rag.rag_agent import RagAgent
from app.rest_api.types.input_types import (
    ChatCompletionInput,
    NewConversationInput,
)
from app.settings import Settings

logger = logging.getLogger(__name__)


# Kubernetes client
config.incluster_config.load_incluster_config()


router = APIRouter()


@router.get("/chats", tags=["Chat"], response_model=list[Chat])
@inject
def get_chats(
    days: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    mongodb: DocumentStoreClient = Depends(Provide[Container.mongodb]),
) -> list[Any]:
    return mongodb.get_chats_for_user(user_id=user.id, days=days)


@router.delete("/chat/{chat_id}", tags=["Chat"])
@inject
async def delete_chat(
    chat_id: str,
    user: User = Depends(get_current_user),
    mongodb: DocumentStoreClient = Depends(Provide[Container.mongodb]),
):
    mongodb.delete_chat(user_id=user.id, chat_id=UUID(chat_id))
    return {
        "status_code": HTTP_202_ACCEPTED,
        "detail": f"Chat `{chat_id}` successfully deleted!",
    }


@router.post("/chat", tags=["Chat"], response_model=Chat)
@inject
async def create_chat(
    body: NewConversationInput,
    user: User = Depends(get_current_user),
    mongodb: DocumentStoreClient = Depends(Provide[Container.mongodb]),
) -> Any:
    try:
        # The title should be no more than 40 characters long. This number is totally
        # arbitrary.
        title = ""
        count = 0
        query_split = body.query.split()
        for w in query_split:
            if len(w) + len(title) <= 40:
                title += f" {w}"
                count += 1
        if count < len(query_split):
            title += "..."
        ts = str(datetime.now(timezone.utc).timestamp())
        c = Chat(
            user_id=user.id,
            namespace=user.namespace,
            chat_id=body.chat_id,
            title=title,
            query=body.query,
            ts=ts,
        )
        mongodb.add_chat(c)
        return c.model_dump()
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/messages/{chat_id}", tags=["Chat"])
@inject
def get_messages(
    chat_id: str,
    user: User = Depends(get_current_user),
    mongodb: DocumentStoreClient = Depends(Provide[Container.mongodb]),
    redis_client: RedisClient = Depends(Provide[Container.redis_client]),
) -> list[dict[str, Any]]:
    # Get the messages from RedisClient, if possible
    messages = redis_client.retrieve_messages_from_redis(chat_id)
    if messages:
        return messages
    else:
        return mongodb.get_messages_from_chat(
            user_id=user.id,
            chat_id=UUID(chat_id),
        )


def create_llm_agent(
    model_provider: ChatModelProvider, model_name: str, api_key: str
) -> Agent:
    with open(Settings.TEMPLATES_ROOT / "main_system_prompt.txt", "r") as f:
        system_prompt = f.read()

    match model_provider:
        case ChatModelProvider.OPENAI:
            model = OpenAIModel(model_name, provider=OpenAIProvider(api_key=api_key))
        case ChatModelProvider.ANTHROPIC:
            model = AnthropicModel(
                model_name, provider=AnthropicProvider(api_key=api_key)
            )
        case ChatModelProvider.GEMINI:
            model = GeminiModel(model_name, provider=GoogleGLAProvider(api_key=api_key))
        case ChatModelProvider.GROQ:
            model = GroqModel(model_name, provider=GroqProvider(api_key=api_key))
        case ChatModelProvider.MISTRAL:
            model = MistralModel(model_name, provider=MistralProvider(api_key=api_key))
        case _:
            raise Exception(f"Unsupported model type: {model_provider}")
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
    )
    return agent


def save_messages_in_document_store(
    user_id: UUID,
    chat_id: UUID,
    result: StreamedRunResult,
    user_message_query: str,
    user_message_context: str,
    citations: list[Citation],
    mongodb: DocumentStoreClient,
    redis_client: RedisClient,
) -> None:
    new_messages = result.new_messages()

    # Replace detailed user query with original user query. Also, ignore the system
    # message.
    for message in new_messages:
        if isinstance(message, ModelRequest):
            request_parts = message.parts
            revised_parts = []
            for part in request_parts:
                if isinstance(part, SystemPromptPart):
                    continue
                elif isinstance(part, UserPromptPart):
                    part.content = user_message_query
                    revised_parts.append(part)
                else:
                    revised_parts.append(part)
            message.parts = revised_parts

    messages_json = to_jsonable_python(new_messages)

    # Add context and IDs to user message
    messages_json[0]["context"] = user_message_context
    messages_json[0]["chat_id"] = str(chat_id)
    messages_json[0]["user_id"] = str(user_id)

    # Add citations and IDs to assistant response
    messages_json[1]["citations"] = [c.model_dump() for c in citations]
    messages_json[1]["chat_id"] = str(chat_id)
    messages_json[1]["user_id"] = str(user_id)

    # Store messages in RedisClient.
    redis_client.add_messages_to_redis(chat_id, messages_json)

    # Store the full response
    mongodb.add_messages_to_chat(
        messages=messages_json,
    )


@router.websocket(
    path="/chat-completion/",
)
@inject
async def websocket_chat_completion(
    websocket: WebSocket,
    mongodb: DocumentStoreClient = Depends(Provide[Container.mongodb]),
    redis_client: RedisClient = Depends(Provide[Container.redis_client]),
    pinecone_client: Pinecone = Depends(Provide[Container.pinecone_client]),
    graph_client: GraphClient = Depends(Provide[Container.graph_client]),
):
    await websocket.accept()
    while True:
        # We receive a message from the user
        try:
            chat_completion_input = await asyncio.wait_for(
                websocket.receive_json(), timeout=1
            )
            if not chat_completion_input:
                continue
            chat_completion_input = ChatCompletionInput(**chat_completion_input)

        # No data, continue the loop
        except asyncio.TimeoutError:
            continue

        except Exception as e:
            print(f"WebSocket `chat-completion` error or disconnect: {e}")
            break  # Exit the loop and close the connection

        # User ID and namespace
        chat = mongodb.get_chat(chat_completion_input.chat_id)
        user_id = UUID(str(chat.user_id))
        namespace = chat.namespace

        # Secret
        operator = KubernetesOperator()
        secret_data = operator.read_namespaced_secret(
            namespace=namespace,
            secret_name=chat_completion_input.chat_model_secret_slug,
        )
        api_key = list(secret_data.values())[0]

        agent = RagAgent(
            namespace=namespace,
            pc=pinecone_client,
            neo4j=graph_client,
            redis_client=redis_client,
            mongodb_client=mongodb,
            chat_model_provider=chat_completion_input.chat_model_provider,
            model_name=chat_completion_input.chat_model_name,
            api_key=api_key,
        )
        chat_history = agent.get_chat_history(user_id, chat_completion_input.chat_id)
        query_context = await agent.build_query_context(
            chat_completion_input.query, chat_history
        )
        user_query_with_context = (
            query_context.detailed_user_query + "\n" + query_context.context_str
            if query_context.context_str
            else query_context.detailed_user_query
        )
        assistant_response_tokens: list[str] = []
        async with agent.llm_agent.run_stream(
            user_prompt=user_query_with_context,
            message_history=chat_history,
        ) as result:
            async for token in result.stream_text(delta=True):
                assistant_response_tokens.append(token)
                await websocket.send_json({"type": "token", "content": token})

        # Citations
        assistant_response_str = "".join(assistant_response_tokens)
        citations = agent.parse_citations_from_response(assistant_response_str)
        citation_documents: list[Citation] = []
        for cit in citations:
            # Full text will probably be pretty large. Store all citation data except
            # the actual content.
            full_citation = query_context.text_context.context_by_citation_number[cit]
            truncated_citation = {
                k: v for k, v in full_citation.items() if k != "content"
            }
            doc = Citation(citation_number=cit, citation=truncated_citation)
            await websocket.send_json(
                {"type": "citation", "content": doc.model_dump_json()}
            )
            citation_documents.append(doc)

        await websocket.send_json({"type": "citation", "content": "done"})
        # After all tokens / citations have been sent, save the messages to our document
        # store.
        save_messages_in_document_store(
            user_id=user_id,
            chat_id=chat_completion_input.chat_id,
            result=result,
            user_message_query=chat_completion_input.query,
            user_message_context=query_context.context_str,
            citations=citation_documents,
            mongodb=mongodb,
            redis_client=redis_client,
        )
