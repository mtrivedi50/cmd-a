import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Tuple

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.clients.graph_client import Edge, FileNode, GraphClient, PersonNode, TextNode
from app.clients.redis_client import RedisClient
from app.clients.vectordb_client import VectorDb, VectorMetadata
from app.db.container import Container
from app.db.factory import Database
from app.db.models.choices import IntegrationType
from app.processors.base.processor import BaseProcessor
from app.processors.base.types import ProcessingChunk
from app.processors.integrations.slack.types import (
    SlackSecret,
)
from app.processors.utils import download_file
from app.rag.types import EdgeRelationship, NodeLabel
from app.settings import Settings

# Logger
logging.basicConfig()
logger = logging.getLogger(__name__)


# Send logs to stdout
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class SlackProcessor(BaseProcessor[ProcessingChunk]):
    """Processes chunks of Slack messages."""

    slack_secret: SlackSecret
    slack_client: WebClient

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
            job_id=job_id,
            chunk_key=chunk_key,
            db=db,
            redis_client=redis_client,
            graph_client=graph_client,
            vector_db=vector_db,
        )

        # Slack client
        token_data = self.read_namespaced_secret(
            namespace=self.namespace,
            secret_name=self.integration_secret.slug,
        )
        self.slack_secret = SlackSecret(**token_data)
        self.slack_client = WebClient(token=self.slack_secret.token)

    def set_chunk_cls(self):
        self.chunk_cls = ProcessingChunk

    def construct_message_id(self, channel_id: str, ts: str):
        """
        Messages are unique identified by their channel ID and timestamp.
        """
        return f"{channel_id}-{ts}"

    def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get user information for a given user ID."""
        try:
            response = self.slack_client.users_info(user=user_id)
            return response["user"]
        except SlackApiError as e:
            logger.error(f"Error getting user info: {e.response['error']}")
            raise

    def get_team_info(self, team_id: str) -> dict[str, Any]:
        """Get team information for a given team ID."""
        try:
            response = self.slack_client.team_info(team=team_id)
            return response["team"]
        except SlackApiError as e:
            logger.error(f"Error getting team info: {e.response['error']}")
            raise

    def slack_to_markdown(self, message: dict[str, Any]) -> str:
        """
        Converts Slack message format to Markdown

        :param message: Slack message object from the API
        :return: Slack message text as Markdown
        """
        if not message or "text" not in message:
            return ""

        text = message["text"]

        # Handle code blocks
        text = re.sub(r"```([\s\S]*?)```", r"```\n\1\n```", text)

        # Handle inline code
        text = re.sub(r"`([^`]+)`", r"`\1`", text)

        # Handle bold
        text = re.sub(r"\*([^*]+)\*", r"**\1**", text)

        # Handle italic
        text = re.sub(r"_([^_]+)_", r"*\1*", text)

        # Handle strikethrough
        text = re.sub(r"~([^~]+)~", r"~~\1~~", text)

        # Handle links - Slack format: <url|text> to Markdown: [text](url)
        text = re.sub(r"<([^|]+)\|([^>]+)>", r"[\2](\1)", text)

        # Handle plain URLs - <url> to url
        text = re.sub(r"<(https?://[^>]+)>", r"\1", text)

        # Handle channel links - <#C12345|channel-name> to #channel-name
        text = re.sub(r"<#([A-Z0-9]+)\|([^>]+)>", r"#\2", text)

        # Handle user mentions - <@U12345|username> to @username
        def replace_user_mention(match):
            user_id, username = match.groups()
            return "@" + (username or user_id)

        text = re.sub(r"<@([A-Z0-9]+)\|?([^>]*)>", replace_user_mention, text)

        # Handle special commands and emoji
        def replace_command(match):
            command = match.group(1)
            parts = command.split("|")
            return parts[1] if len(parts) > 1 else parts[0]

        text = re.sub(r"<!([^>]+)>", replace_command, text)

        # Process message attachments if available
        if "attachments" in message and message["attachments"]:
            text += "\n\n"
            for attachment in message["attachments"]:
                # Add attachment title as heading
                if "title" in attachment and attachment["title"]:
                    text += f"### {attachment['title']}\n\n"

                # Add attachment text
                if "text" in attachment and attachment["text"]:
                    text += f"{attachment['text']}\n\n"

                # Add attachment fields as bullet points
                if "fields" in attachment and attachment["fields"]:
                    for field in attachment["fields"]:
                        text += f"- **{field['title']}**: {field['value']}\n"
                    text += "\n"

                # Add attachment image if available
                if "image_url" in attachment and attachment["image_url"]:
                    text += f"![Image]({attachment['image_url']})\n\n"

        # Handle blocks (for newer Slack messages)
        if "blocks" in message and message["blocks"]:
            for block in message["blocks"]:
                if (
                    block["type"] == "section"
                    and "text" in block
                    and "text" in block["text"]
                ):
                    # Process section blocks
                    block_text = block["text"]["text"]
                    text += block_text + "\n\n"
                elif block["type"] == "image" and "image_url" in block:
                    # Process image blocks
                    alt_text = block.get("alt_text", "Image")
                    text += f"![{alt_text}]({block['image_url']})\n\n"

        # Normalize line endings and trim extra whitespace
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        return text

    def grab_non_text_elements_from_block(
        self, block: dict[str, Any], element_type: str
    ) -> list[dict[str, Any]]:
        nested_elements: list[dict[str, Any]] = []
        block_elements = block.get("elements", [])
        for elt in block_elements:
            elt_type = elt.get("type", "")
            if elt_type == "text":
                continue

            # We only care about links and user mentions for now
            elif elt_type == element_type:
                nested_elements.append(elt)

            # Recursively call this function to grab nested elements
            nested_elements += self.grab_non_text_elements_from_block(elt, element_type)

        return nested_elements

    def grab_non_text_message_elements(
        self,
        blocks: list[dict[str, Any]],
        element_type: str,
    ) -> list[dict[str, Any]]:
        non_text_elements: list[dict[str, Any]] = []
        for block in blocks:
            non_text_elements += self.grab_non_text_elements_from_block(
                block, element_type
            )
        return non_text_elements

    def define_metadata_from_message_dict(
        self, message: dict[str, Any]
    ) -> Tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        """
        Super simple function that removes the `files` and `blocks` keys from the
        base `message` dict and returns them (alongside the updated `message` dict).
        """
        message_copy = message.copy()
        files = message_copy.pop("files", [])
        blocks = message_copy.pop("blocks", [])
        return files, blocks, message_copy

    def construct_message_url(
        self, message_ts: str, message: dict[str, Any]
    ) -> str | None:
        team_info: dict[str, Any] | None = None
        team_id = message.get("team", None)
        if team_id:
            team_info = self.get_team_info(team_id)

        # Construct public message URL
        message_url: str | None = None
        if team_info:
            domain = team_info["url"]
            message_url = f"{domain}archives/{self.chunk.parent_group_id}/p{message_ts.replace('.', '')}"

        return message_url

    def save_message_graph_entities(
        self,
        message: dict[str, Any],
        parent_message_id: str | None = None,
    ):
        message_ts = message["ts"]
        message_id = self.construct_message_id(self.chunk.parent_group_id, message_ts)

        # User
        user_id = message.get("user", None)
        if user_id:
            user_info = self.get_user_info(user_id)
            if user_info.get("name", ""):
                user_node = PersonNode(
                    integration_id=self.integration_id,
                    id=user_id,
                    labels=[NodeLabel.PERSON],
                    source=IntegrationType.SLACK,
                    name_login=user_info.get("name", ""),
                )
                self.graph_client.add_node(user_node)

        # Message node. For the node properties, remove `blocks` and `files`. These are
        # processed separately.
        files, blocks, message = self.define_metadata_from_message_dict(message)
        message_text_as_md = self.slack_to_markdown(message)

        # Message URL
        message_url = self.construct_message_url(message_ts, message)

        # Add message node
        message_node = TextNode(
            integration_id=self.integration_id,
            id=message_id,
            labels=[NodeLabel.TEXT],
            source=IntegrationType.SLACK,
            content=message_text_as_md,
            ts=str(message["ts"]),
            url=message_url,
            display_name="Slack Message",
            reactions=[r["name"] for r in message.get("reactions", [])],
        )
        self.graph_client.add_node(message_node)

        # Entity resolution. Message links are in the form:
        # {'type': 'link', 'url': '...}
        message_links = self.grab_non_text_message_elements(blocks, "link")
        for link in message_links:
            link_nodes = self.graph_client.get_nodes_from_url(link["url"])

            # If the node doesn't exist (e.g., if a GitHub PR is references a new Slack
            # thread we have not parsed), then create a temporary node. We will update
            # the node when we parse Slack.
            if not link_nodes:
                # Node with some temporary attributes. These will pretty much all get
                # updated later, even the source.
                temporary_node_for_message_link = TextNode(
                    integration_id=self.integration_id,
                    id=link["url"],
                    labels=[NodeLabel.TEXT],
                    source=IntegrationType.SLACK,
                    content=link["url"],
                    ts="",
                    url=link["url"],
                    display_name="",
                    reactions=[],
                )
                self.graph_client.add_node(temporary_node_for_message_link)
                entities_are_associated = Edge(
                    from_node_id=message_id,
                    to_node_id=link["url"],
                    relationship_type=EdgeRelationship.LINKED_TO,
                )
                self.graph_client.add_edge(entities_are_associated)

            else:
                for node in link_nodes:
                    entities_are_associated = Edge(
                        from_node_id=message_id,
                        to_node_id=node["id"],
                        relationship_type=EdgeRelationship.LINKED_TO,
                    )
                    self.graph_client.add_edge(entities_are_associated)

        # Files
        for message_file in files:
            file_node = FileNode(
                integration_id=self.integration_id,
                id=message_file["id"],
                labels=[NodeLabel.FILE],
                source=IntegrationType.SLACK,
                name=message_file["name"],
                mimetype=message_file["mimetype"],
                url=message_file["url_private"],
            )
            self.graph_client.add_node(file_node)

        # Replies
        if "thread_ts" in message and message["thread_ts"] == message["ts"]:
            if parent_message_id:
                raise Exception("Message reply cannot be the parent of a thread!")
            try:
                replies = self.slack_client.conversations_replies(
                    channel=self.chunk.parent_group_id, ts=str(message["ts"])
                )

                # Skip the parent message, recursively save graph entities
                reply_messages = replies["messages"][1:]
                for reply in reply_messages:
                    self.save_message_graph_entities(
                        reply,
                        message_id,
                    )
            except SlackApiError as e:
                logger.error(f"Error getting thread replies: {e.response['error']}")

        # If message is a reply, create an edge
        if parent_message_id:
            parent_message_has_reply_edge = Edge(
                from_node_id=parent_message_id,
                to_node_id=message_id,
                relationship_type=EdgeRelationship.HAS,
            )
            self.graph_client.add_edge(parent_message_has_reply_edge)

        # User posted the message
        if user_id:
            user_posted_message_edge = Edge(
                from_node_id=user_id,
                to_node_id=message_id,
                relationship_type=EdgeRelationship.CREATED,
            )
            self.graph_client.add_edge(user_posted_message_edge)

        # Message has file
        for _file in files:
            message_has_file_edge = Edge(
                from_node_id=message_id,
                to_node_id=_file["id"],
                relationship_type=EdgeRelationship.HAS,
            )
            self.graph_client.add_edge(message_has_file_edge)

    def save_chunk_graph_entities(self, content: dict[str, Any]):
        self.save_message_graph_entities(content)

    def upsert_chunk_embeddings(self, content: dict[str, Any]):
        message_ts = content["ts"]
        message_id = self.construct_message_id(self.chunk.parent_group_id, message_ts)

        # Message text
        message_text_md = self.slack_to_markdown(content)
        files, _, _ = self.define_metadata_from_message_dict(content)

        # Metadata. This will be a subset of what we store in our graph database
        # (basically, just the message ID and integration ID).
        message_metadata = VectorMetadata(
            id=message_id,
            source=IntegrationType.SLACK,
            integration_id=self.integration_id,
            display_name="Slack Message",
        )
        self.vector_db.process_markdown_text(
            self.namespace,
            message_text_md,
            message_metadata.model_dump(),
            self.chunk.parent_group_id,
        )

        # Message files - we need to download these locally
        local_paths: list[Path] = []
        file_metadatas: list[VectorMetadata] = []
        for file_properties in files:
            if file_properties.get("url_private_download", "") and file_properties.get(
                "name", ""
            ):
                slack_file_metadata = VectorMetadata(
                    id=file_properties["id"],
                    source=IntegrationType.SLACK,
                    integration_id=self.integration_id,
                    display_name="Slack File",
                )
                try:
                    local_file = Path(
                        Settings.ROOT / self.namespace / file_properties["name"]
                    )
                    logger.info(f"Downloading file to local path {local_file}")
                    download_file(
                        url=file_properties["url_private_download"],
                        headers={"Authorization": f"Bearer {self.slack_secret.token}"},
                        local_file=local_file,
                    )
                    local_paths.append(local_file)
                    file_metadatas.append(slack_file_metadata)
                except Exception as e:
                    error_metadata = {
                        "file_name": file_properties.get("name", ""),
                        "channel_id": self.chunk.parent_group_id,
                        "message_ts": content.get("ts", ""),
                        "user_namespace": self.namespace,
                        "exception_tb": str(e),
                    }
                    logger.error(
                        f"Could not download document: {json.dumps(error_metadata)}"
                    )

        self.vector_db.process_documents(
            namespace=self.namespace,
            local_file_paths=local_paths,
            file_metadatas=file_metadatas,
            parent_group_id=self.chunk.parent_group_id,
        )

        # After we process the documents, remove them locally
        for local_file in local_paths:
            logger.info(f"Removing local file {local_file}")
            os.remove(local_file)


if __name__ == "__main__":
    container = Container()
    container.init_resources()

    # Other environment variables
    integration_id = os.getenv("INTEGRATION_ID", None)
    if not integration_id:
        raise Exception("`INTEGRATION_ID` environment variable not defined!")

    namespace = os.getenv("NAMESPACE", None)
    if not namespace:
        raise Exception("`NAMESPACE` environment variable not defined!")

    chunk_data_key = os.getenv("CHUNK_DATA_KEY", None)
    if not chunk_data_key:
        raise Exception(
            "`CHUNK_DATA_KEY` not provided to chunk processor via environment variable!"
        )

    job_id = os.getenv("JOB_ID", None)
    if not job_id:
        raise Exception(
            "`JOB_ID` not provided to chunk processor via environment variable!"
        )

    processor = SlackProcessor(
        integration_id=integration_id,
        namespace=namespace,
        job_id=job_id,
        chunk_key=chunk_data_key,
        db=container.database(),
        redis_client=container.redis_client(),
        graph_client=container.graph_client(),
        vector_db=container.vector_db(),
    )
    processor.process_chunk_data()
