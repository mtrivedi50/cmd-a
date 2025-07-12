import json
import logging
import re
import sys
from abc import abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from app.clients.graph_client import GraphClient
from app.clients.redis_client import RedisClient
from app.clients.vectordb_client import VectorDb
from app.db.factory import Database
from app.db.models.choices import IntegrationStatus
from app.db.models.integration import ChunkProcessingJob, ParentGroupData
from app.processors.base.component import BaseProcessingComponent
from app.processors.base.types import ProcessingChunk

# Logger
logging.basicConfig()
logger = logging.getLogger(__name__)


# Send logs to stdout
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


T = TypeVar("T", bound=ProcessingChunk)


class MarkdownLink(BaseModel):
    text: str
    url: str


class MarkdownUserTag(BaseModel):
    tag_type: str
    user_id: str
    display_text: str


class BaseProcessor(BaseProcessingComponent, Generic[T]):
    """
    Base class for all chunk processors. Chunks are created via the integration's
    parent processor.
    """

    job_id: str
    chunk_key: str
    graph_client: GraphClient
    vector_db: VectorDb

    # Parent group data from database
    parent_group_data: ParentGroupData
    # Chunk class and data
    chunk_cls: type[T]
    chunk: T

    def __init__(
        self,
        *,
        integration_id: str,
        namespace: str,
        job_id: str,
        chunk_key: str,
        db: Database,
        redis_client: RedisClient,
        graph_client: GraphClient,
        vector_db: VectorDb,
    ):
        super().__init__(
            integration_id=integration_id,
            namespace=namespace,
            db=db,
            redis_client=redis_client,
        )
        self.job_id = job_id
        self.chunk_key = chunk_key
        self.graph_client = graph_client
        self.vector_db = vector_db

        # Chunk data
        chunk_data = self.redis_client.simple_get(self.chunk_key)
        if chunk_data is None:
            raise Exception(
                f"Could not find any data in Redis with key `{self.chunk_key}`!"
            )
        self.set_chunk_cls()
        self.chunk = self.chunk_cls(**json.loads(chunk_data))

        # Parent Group database object
        parent_group_data_obj = self.db.get_object(
            db_type=ParentGroupData,
            where_conditions={
                "parent_group_id": self.chunk.parent_group_id,
                "integration_id": self.integration_id,
            },
        )
        self.parent_group_data = parent_group_data_obj

        # The processing job is now running
        self.set_chunk_processing_job_status(IntegrationStatus.RUNNING)

    def set_chunk_cls(self):
        raise Exception("`set_chunk_cls` must be implemented!")

    @property
    def num_processed_nodes(self) -> int:
        return self.graph_client.get_node_count(self.chunk.parent_group_id)

    @property
    def num_processed_edges(self) -> int:
        return self.graph_client.get_edge_count(self.chunk.parent_group_id)

    @property
    def num_processed_records(self) -> int:
        return self.vector_db.get_record_count(self.chunk.parent_group_id)

    def parse_markdown_user_tags(self, markdown_text: str) -> list[MarkdownUserTag]:
        """
        Extract user tags/mentions from markdown text.

        This function extracts different formats of user mentions:
        - Slack-style: <@U12345>
        - GitHub-style: @username
        - Custom markdown: [@username](user:username)
        """
        tags = []

        # Slack-style mentions: <@U12345> or <@U12345|display_name>
        slack_pattern = r"<@(U[A-Z0-9]+)(?:\|([^>]+))?>"
        for match in re.finditer(slack_pattern, markdown_text):
            groups = match.groups()
            user_id = groups[0]
            display_text = groups[1] if len(groups) > 1 and groups[1] else user_id

            tags.append(
                MarkdownUserTag(
                    tag_type="slack",
                    user_id=user_id,
                    display_text=display_text,
                )
            )

        # GitHub-style mentions: @username
        # Username pattern based on GitHub's rules: alphanumeric with single hyphens in between
        github_pattern = r"(?<!\w)@([a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38})"
        for match in re.finditer(github_pattern, markdown_text):
            username = match.group(1)
            tags.append(
                MarkdownUserTag(
                    tag_type="github", user_id=username, display_text=f"@{username}"
                )
            )

        # Custom markdown user links: [@username](user:username)
        custom_pattern = r"\[@([^\]]+)\]\(user:([^)]+)\)"
        for match in re.finditer(custom_pattern, markdown_text):
            display_name, username = match.groups()
            tags.append(
                MarkdownUserTag(
                    tag_type="custom", user_id=username, display_text=display_name
                )
            )

        # Email-like mentions: user@domain.com
        email_pattern = r"(?<!\S)([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?!\S)"
        for match in re.finditer(email_pattern, markdown_text):
            email = match.group(1)
            tags.append(
                MarkdownUserTag(tag_type="email", user_id=email, display_text=email)
            )

        return tags

    def parse_markdown_links(self, markdown_text: str) -> list[MarkdownLink]:
        """
        Parse all links from markdown text.

        This function extracts both:
        - Standard markdown links: [text](url)
        - Reference-style links: [text][reference] ... [reference]: url
        - Bare URLs: http(s)://example.com
        """
        links = []

        # Pattern for standard markdown links: [text](url)
        inline_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        for match in re.finditer(inline_pattern, markdown_text):
            text, url = match.groups()
            links.append(MarkdownLink(text=text.strip(), url=url.strip()))

        # Pattern for reference-style links
        # First find all reference definitions: [ref]: url
        references = {}
        ref_pattern = r'^\s*\[([^\]]+)\]:\s*(\S+)(?:\s+"([^"]+)")?\s*$'
        for line in markdown_text.split("\n"):
            ref_match = re.match(ref_pattern, line)
            if ref_match:
                ref_id, url, title = (
                    ref_match.groups()
                    if len(ref_match.groups()) == 3
                    else (*ref_match.groups(), None)
                )
                references[ref_id.lower()] = url

        # Then find all reference usages: [text][ref]
        ref_usage_pattern = r"\[([^\]]+)\]\[([^\]]*)\]"
        for ref_usage_match in re.finditer(ref_usage_pattern, markdown_text):
            text, ref_id = ref_usage_match.groups()
            # If ref_id is empty, use text as the reference
            ref_id = ref_id.lower() if ref_id else text.lower()
            if ref_id in references:
                links.append(MarkdownLink(text=text.strip(), url=references[ref_id]))

        # Pattern for bare URLs
        url_pattern = r'(?<!\(|\[)(https?://[^\s<>"\')]+)(?!\)|\])'
        for bare_match in re.finditer(url_pattern, markdown_text):
            url = bare_match.group(1)
            links.append(MarkdownLink(text=url, url=url))

        return links

    @abstractmethod
    def save_chunk_graph_entities(self, content: dict[str, Any]) -> None:
        """Process graph entities (nodes, edges) and save to Neo4J"""
        pass

    @abstractmethod
    def upsert_chunk_embeddings(self, content: dict[str, Any]) -> None:
        """Process chunk content (text and files) and save to Pinecone"""
        pass

    def update_parent_group_data_count_attributes(self, attributes: dict[str, int]):
        with self.db.session() as session:
            parent_group_data = self.db.get_object(
                db_type=ParentGroupData,
                where_conditions={
                    "parent_group_id": self.chunk.parent_group_id,
                    "integration_id": self.integration_id,
                },
                session=session,
            )
            for count_attr, count_value in attributes.items():
                setattr(parent_group_data, count_attr, count_value)
            session.commit()
            session.refresh(parent_group_data)

    def process_chunk_data(self) -> None:
        """Process the actual chunk data"""
        error_json = {
            "parent_group_id": self.chunk.parent_group_id,
            "chunk_id": self.chunk.id,
        }

        # Update the database after each chunk. This may lead to a bunch of database
        # requests, in which case we can adjust this to update after all chunks are
        # processed.
        for content in self.chunk.content:
            try:
                self.save_chunk_graph_entities(content=content)
                self.update_parent_group_data_count_attributes(
                    {
                        "node_count": self.num_processed_nodes,
                        "edge_count": self.num_processed_edges,
                    }
                )

            except Exception as e1:
                error_json["detail"] = str(e1)
                logger.error(
                    f"Error saving the graph entities: {json.dumps(error_json)}"
                )
                # We update the integration / parent group status based on the statuses
                # of all associated processing jobs via a Websocket.
                self.set_chunk_processing_job_status(IntegrationStatus.FAILED)
                raise

            try:
                self.upsert_chunk_embeddings(content=content)
                self.update_parent_group_data_count_attributes(
                    {
                        "record_count": self.num_processed_records,
                    }
                )
            except Exception as e2:
                error_json["detail"] = str(e2)
                logger.error(
                    f"Error upserting chunk embeddings: {json.dumps(error_json)}"
                )
                # We update the integration / parent group status based on the statuses
                # of all associated processing jobs via a Websocket.
                self.set_chunk_processing_job_status(IntegrationStatus.FAILED)
                raise

        self.set_integration_status(IntegrationStatus.SUCCESS)

    def set_chunk_processing_job_status(self, status: IntegrationStatus) -> None:
        with self.db.session() as session:
            processing_job_db_obj = self.db.get_object(
                db_type=ChunkProcessingJob,
                where_conditions={"id": self.job_id},
                session=session,
            )
            processing_job_db_obj.status = status
            session.commit()
            session.refresh(processing_job_db_obj)
