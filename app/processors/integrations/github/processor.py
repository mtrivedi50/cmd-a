import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Tuple
from urllib.parse import urlparse

from app.clients.graph_client import Edge, FileNode, GraphClient, PersonNode, TextNode
from app.clients.redis_client import RedisClient
from app.clients.vectordb_client import VectorDb, VectorMetadata
from app.db.container import Container
from app.db.factory import Database
from app.db.models.choices import IntegrationStatus, IntegrationType
from app.processors.base.processor import BaseProcessor, MarkdownLink
from app.processors.constants import (
    SUPPORTED_INPUT_FORMATS,
)
from app.processors.integrations.github.api import GithubClient
from app.processors.integrations.github.types import (
    ContentType,
    GithubProcessingChunk,
    GithubSecret,
)
from app.rag.types import (
    EdgeRelationship,
    NodeLabel,
)
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


class GithubProcessor(BaseProcessor[GithubProcessingChunk]):
    """Processes chunks of GitHub PRs and issues."""

    github_secret: GithubSecret
    github_client: GithubClient

    def __init__(
        self,
        *,
        processor_integration_id: str,
        processor_namespace: str,
        processor_job_id: str,
        chunk_key: str,
        db: Database,
        redis_client: RedisClient,
        graph_client: GraphClient,
        vector_db: VectorDb,
    ):
        super().__init__(
            integration_id=processor_integration_id,
            namespace=processor_namespace,
            job_id=processor_job_id,
            chunk_key=chunk_key,
            db=db,
            redis_client=redis_client,
            graph_client=graph_client,
            vector_db=vector_db,
        )

        # GitHub client
        token_data = self.read_namespaced_secret(
            namespace=self.namespace,
            secret_name=self.integration_secret.slug,
        )
        self.github_secret = GithubSecret(**token_data)
        self.github_client = GithubClient(secret=self.github_secret)

    def set_chunk_cls(self):
        self.chunk_cls = GithubProcessingChunk

    def _add_comments_nodes_edges(self, comments_url: str, from_node_id: str):
        """Process PR / issue comments"""
        comments = self.github_client.execute_simple_get_request(comments_url)

        for comment in comments:
            comment_id = comment["id"]
            comment_body_links = self.parse_markdown_links(
                comment.get("body", "") or ""
            )

            # Node
            comment_reactions_list = []
            comment_reaction_url = comment.get("reactions", {}).get("url", None)
            if comment_reaction_url:
                comment_reactions = self.github_client.execute_simple_get_request(
                    comment_reaction_url
                )
                comment_reactions_list = [r["content"] for r in comment_reactions]

            comment_node = TextNode(
                integration_id=self.integration_id,
                id=str(comment_id),
                labels=[NodeLabel.TEXT],
                source=IntegrationType.GITHUB,
                content=comment.get("body", "") or "",
                ts=comment["created_at"],
                url=comment["html_url"],
                display_name="GitHub Comment",
                reactions=comment_reactions_list,
            )
            self.graph_client.add_node(comment_node)

            # Files
            self._process_file_links_and_perform_entity_resolution(
                comment_body_links, from_node_id=comment_id
            )

            # PR has the comment
            pr_has_comment_edge = Edge(
                from_node_id=from_node_id,
                to_node_id=comment_id,
                relationship_type=EdgeRelationship.HAS,
            )
            self.graph_client.add_edge(pr_has_comment_edge)

    @staticmethod
    def _get_file_name_type_from_github_url(url: str) -> Tuple[str, str]:
        """
        Extracts the file type (extension) from a GitHub-hosted file URL. Example:
        'https://user-images.githubusercontent.com/.../image.png' → 'png'

        In the future, we could infer file type from MIME headers instead (e.g., via a
        HEAD request).
        """
        path = urlparse(url).path
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        return name, ext.lstrip(".").lower() if ext else "unknown"

    def _process_file_links_and_perform_entity_resolution(
        self, body_links: list[MarkdownLink], from_node_id: str
    ):
        """
        Process files from PRs / issues. Note that files are represented as links hosted
        on GitHub's CDN (e.g., https://user-images.githubusercontent.com/...).
        """
        for link in body_links:
            # We only care about files that we can process and embed
            file_name, file_ext = self._get_file_name_type_from_github_url(link.url)
            if file_ext in SUPPORTED_INPUT_FORMATS:
                # Node
                file_node = FileNode(
                    integration_id=self.integration_id,
                    id=f"{file_name}.{file_ext}-{link.url}",
                    labels=[NodeLabel.FILE],
                    source=IntegrationType.GITHUB,
                    name=file_name,
                    mimetype=file_ext,
                    url=link.url,
                )
                self.graph_client.add_node(file_node)

                # Parent node has this file
                parent_node_has_file_edge = Edge(
                    from_node_id=from_node_id,
                    to_node_id=link.url,
                    relationship_type=EdgeRelationship.HAS,
                )
                self.graph_client.add_edge(parent_node_has_file_edge)

            # Otherwise, perform entity resolution via the link.
            else:
                link_nodes = self.graph_client.get_nodes_from_url(link.url)

                # If the node doesn't exist (e.g., if a GitHub PR is references a new Slack
                # thread we have not parsed), then create a temporary node. We will update
                # the node when we parse Slack.
                if not link_nodes:
                    # Node with some temporary attributes. These will pretty much all get
                    # updated later.
                    temporary_node_for_message_link = TextNode(
                        integration_id=self.integration_id,
                        id=link.url,
                        labels=[NodeLabel.TEXT],
                        source=IntegrationType.GITHUB,
                        content=link.url,
                        ts="",
                        url=link.url,
                        display_name="",
                        reactions=[],
                    )
                    self.graph_client.add_node(temporary_node_for_message_link)
                    entities_are_associated = Edge(
                        from_node_id=from_node_id,
                        to_node_id=link.url,
                        relationship_type=EdgeRelationship.LINKED_TO,
                    )
                    self.graph_client.add_edge(entities_are_associated)

                else:
                    for node in link_nodes:
                        entities_are_associated = Edge(
                            from_node_id=from_node_id,
                            to_node_id=node["id"],
                            relationship_type=EdgeRelationship.LINKED_TO,
                        )
                        self.graph_client.add_edge(entities_are_associated)

    def _construct_pr_issue_id(self, content_type: ContentType, pr_issue_number: int):
        """Construct PR / issue ID. Used for node IDs and embedding IDs."""
        return f"{self.chunk.parent_group_id}-{content_type}{pr_issue_number}"

    def save_issue_graph_entities(
        self, issue: dict[str, Any], issue_id: str | None = None
    ):
        """Save graph entities for an issue. This includes:

        - The issue itself
        - The issue's reactions
        - The issue's comments
        - The issue's comments' reactions
        """
        processed_issue_id = (
            issue_id
            if issue_id
            else self._construct_pr_issue_id(
                content_type=ContentType.ISSUE, pr_issue_number=issue["number"]
            )
        )
        issue_body_links = self.parse_markdown_links(issue.get("body", "") or "")

        # Issue reactions
        issue_reactions_list = []
        issue_reactions_url = issue.get("reactions", {}).get("url", None)
        if issue_reactions_url:
            reactions = self.github_client.execute_simple_get_request(
                issue_reactions_url
            )
            issue_reactions_list = [r["content"] for r in reactions]
        issue_node = TextNode(
            integration_id=self.integration_id,
            id=processed_issue_id,
            labels=[NodeLabel.TEXT],
            source=IntegrationType.GITHUB,
            content="\n".join(
                list(
                    filter(
                        None,
                        [issue.get("title", "") or "", issue.get("body", "") or ""],
                    )
                )
            ),
            ts=issue["created_at"],
            url=issue["html_url"],
            display_name="GitHub Issue",
            reactions=issue_reactions_list,
        )
        self.graph_client.add_node(issue_node)

        # Files
        self._process_file_links_and_perform_entity_resolution(
            issue_body_links, from_node_id=processed_issue_id
        )

        # Issue comments
        issue_comments_url: str | None = issue.get("comments_url")
        if issue_comments_url:
            self._add_comments_nodes_edges(
                comments_url=issue_comments_url, from_node_id=processed_issue_id
            )

    def save_pr_graph_entities(self, pr: dict[str, Any]):
        """Save graph entities for a PR. This includes:

        - The PR itself
        - The PR creator
        - The PR issue (and all associated graph entities, see
          `save_issue_graph_entities` for more information)
        - The PR reactions
        - The PR review comments
        - The PR review comments' reactions
        """
        pr_id = self._construct_pr_issue_id(
            content_type=ContentType.PR, pr_issue_number=pr["number"]
        )

        # Pull request node. Per the documentation, the default `body` in the pull
        # request contains raw markdown:
        # https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests
        pr_body_links = self.parse_markdown_links(pr.get("body", "") or "")

        # PR reactions
        pr_reactions_list = []
        pr_reactions_url = pr.get("reactions", {}).get("url")
        if pr_reactions_url:
            pr_reactions = self.github_client.execute_simple_get_request(
                pr_reactions_url
            )
            pr_reactions_list = [r["content"] for r in pr_reactions]
        pr_node = TextNode(
            integration_id=self.integration_id,
            id=pr_id,
            labels=[NodeLabel.TEXT],
            source=IntegrationType.GITHUB,
            content="\n".join(
                list(
                    filter(None, [pr.get("title", "") or "", pr.get("body", "") or ""])
                )
            ),
            ts=pr["created_at"],
            url=pr["html_url"],
            display_name="GitHub PR",
            reactions=pr_reactions_list,
        )
        self.graph_client.add_node(pr_node)

        # Determine if the links are files. If they are, then add those nodes /
        # relationships to the graph.
        self._process_file_links_and_perform_entity_resolution(
            pr_body_links, from_node_id=pr_id
        )

        # PR creator
        pr_creator: str | None = pr.get("user", {}).get("login", None)
        if pr_creator:
            pr_creator_user_info = self.github_client.get_user(login=pr_creator)
            pr_creator_node = PersonNode(
                integration_id=self.integration_id,
                id=pr_creator,
                labels=[NodeLabel.PERSON],
                source=IntegrationType.GITHUB,
                name_login=pr_creator_user_info.get("name", "") or pr_creator,
            )
            self.graph_client.add_node(pr_creator_node)

            # User created PR edge
            user_created_pr_edge = Edge(
                from_node_id=pr_creator,
                to_node_id=pr_id,
                relationship_type=EdgeRelationship.CREATED,
            )
            self.graph_client.add_edge(user_created_pr_edge)

        # Issue
        pr_issue_url = pr.get("issue_url")
        if pr_issue_url:
            pr_issue_json = self.github_client.execute_simple_get_request(pr_issue_url)

            # There should only be one issue, but we always return a list from our
            # makeshift client. For convenience, just iterate through the returned list.
            for pr_issue_info in pr_issue_json:
                issue_id = self._construct_pr_issue_id(
                    content_type=ContentType.ISSUE,
                    pr_issue_number=pr_issue_info["number"],
                )
                self.save_issue_graph_entities(
                    issue=pr_issue_info,
                    issue_id=issue_id,
                )

                # PR addresses issue
                pr_addresses_issue_edge = Edge(
                    from_node_id=issue_id,
                    to_node_id=pr_id,
                    relationship_type=EdgeRelationship.LINKED_TO,
                )
                self.graph_client.add_edge(pr_addresses_issue_edge)

        # PR comments
        pr_review_comments_url: str | None = pr.get("review_comments_url")
        if pr_review_comments_url:
            self._add_comments_nodes_edges(
                comments_url=pr_review_comments_url, from_node_id=pr_id
            )

    def save_chunk_graph_entities(self, content: dict[str, Any]):
        """Save PR and/or issue graph entities. If a PR is associated with an issue, then we
        may end up doing a bit of duplicative work (i.e., save issue node when
        processing the PR, save issue node again when processing all the issues).
        This shouldn't be too big a deal; we're using consistent node IDs, and our graph
        client gracefully handles cases where a node already exists.
        """
        if self.chunk.content_type == ContentType.PR:
            self.save_pr_graph_entities(pr=content)
        elif self.chunk.content_type == ContentType.ISSUE:
            self.save_issue_graph_entities(issue=content)
        else:
            self.set_parent_group_data_status(
                parent_group_id=self.chunk.parent_group_id,
                status=IntegrationStatus.FAILED,
            )
            self.set_integration_status(IntegrationStatus.FAILED)
            raise Exception(f"Unrecognized contented type `{self.chunk.content_type}`!")

    def upsert_chunk_embeddings(self, content: dict[str, Any]):
        """Save PR and/or issue embeddings. If a PR is associated with an issue, then we
        may end up doing a bit of duplicative work (see `save_chunk_graph_entities` for
        more information). This shouldn't be a big deal.
        """
        pr_issue_id = self._construct_pr_issue_id(
            content_type=self.chunk.content_type, pr_issue_number=content["number"]
        )

        # Display name
        if self.chunk.content_type == ContentType.PR:
            display_name = "PR"
        else:
            display_name = "Issue"
        metadata = VectorMetadata(
            id=pr_issue_id,
            source=IntegrationType.GITHUB,
            integration_id=self.integration_id,
            display_name=f"GitHub {display_name}",
        )
        if content["body"]:
            self.vector_db.process_markdown_text(
                self.namespace,
                content["body"],
                metadata.model_dump(),
                self.chunk.parent_group_id,
            )

        # Attachments. Attachments are uploaded as links hosted on GitHub's CDN
        # (https://user-images.githubusercontent.com/...) when users drag/drop files
        # into comments or PR/issue bodies.
        local_paths: list[Path] = []
        file_metadatas: list[VectorMetadata] = []
        pr_issue_body_links = self.parse_markdown_links(content.get("body", "") or "")
        for file_link in pr_issue_body_links:
            # Check if URL is one of the allowed formats
            file_name, file_type = self._get_file_name_type_from_github_url(
                file_link.url
            )
            if file_type in SUPPORTED_INPUT_FORMATS:
                file_metadata = VectorMetadata(
                    id=file_link.url,
                    source=IntegrationType.GITHUB,
                    integration_id=self.integration_id,
                    display_name="GitHub File",
                )
                try:
                    local_file = Settings.ROOT / self.namespace / file_name
                    logger.info(f"Downloading file to local path {local_file}")
                    self.github_client.download_file(
                        url=file_link.url,
                        local_path=local_file,
                    )
                    local_paths.append(local_file)
                    file_metadatas.append(file_metadata)
                except Exception as e:
                    error_metadata = {
                        "file_name": file_name,
                        "repo_id": self.chunk.parent_group_id,
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

    processor = GithubProcessor(
        processor_integration_id=integration_id,
        processor_namespace=namespace,
        processor_job_id=job_id,
        chunk_key=chunk_data_key,
        db=container.database(),
        redis_client=container.redis_client(),
        graph_client=container.graph_client(),
        vector_db=container.vector_db(),
    )
    processor.process_chunk_data()
