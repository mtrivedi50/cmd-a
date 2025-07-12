import asyncio
import logging
import os
import sys
from typing import Any, Generator

from app.clients.redis_client import RedisClient
from app.db.container import Container
from app.db.factory import Database
from app.db.models.choices import IntegrationStatus
from app.processors.base.types import ProcessingChunk, ProcessingParentGroupData
from app.processors.base.worker import BaseWorker
from app.processors.integrations.github.api import GithubClient
from app.processors.integrations.github.types import (
    ContentType,
    GithubProcessingChunk,
    GithubSecret,
)
from app.settings import Settings

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Send logs to stdout
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class GithubWorker(BaseWorker):
    """Worker for processing Slack channels"""

    github_secret: GithubSecret
    github_client: GithubClient

    def __init__(
        self,
        *,
        worker_integration_id: str,
        worker_namespace: str,
        db: Database,
        redis_client: RedisClient,
    ):
        super().__init__(
            integration_id=worker_integration_id,
            namespace=worker_namespace,
            db=db,
            redis_client=redis_client,
        )

        # GitHub client
        token_data = self.read_namespaced_secret(
            namespace=self.namespace,
            secret_name=self.integration_secret.slug,
        )
        self.github_secret = GithubSecret(**token_data)
        self.github_client = GithubClient(secret=self.github_secret)

    def create_chunks(
        self, data: ProcessingParentGroupData
    ) -> Generator[GithubProcessingChunk, None, None]:
        """Process PRs and issues from a GitHub repository in chunks."""
        try:
            # Start with PRs
            pr_chunk_id = 0
            pr_chunk_content: list[dict[str, Any]] = []
            pr_page_generator = self.github_client.get_pull_requests(
                repo_full_name=data.id, since=data.oldest
            )
            for pr_page in pr_page_generator:
                for pr in pr_page:
                    if len(pr_chunk_content) >= Settings.MAX_OBJECTS_IN_JOB:
                        logger.info(
                            f"Processing {len(pr_chunk_content)} PRs for Github repository {data.id}..."
                        )
                        yield GithubProcessingChunk(
                            id=str(pr_chunk_id),
                            parent_group_id=data.id,
                            parent_group_raw_api_response=data.raw_api_response,
                            ts=data.oldest,
                            content_type=ContentType.PR,
                            content=pr_chunk_content,
                        )
                        pr_chunk_content = []
                        pr_chunk_id += 1
                    else:
                        pr_chunk_content.append(pr)

            # Always yield remaining PRs, even if less than chunk size
            if pr_chunk_content:
                logger.info(
                    f"Processing {len(pr_chunk_content)} PRs for Github repository {data.id}..."
                )
                yield GithubProcessingChunk(
                    id=str(pr_chunk_id),
                    parent_group_id=data.id,
                    parent_group_raw_api_response=data.raw_api_response,
                    ts=data.oldest,
                    content_type=ContentType.PR,
                    content=pr_chunk_content,
                )

            # Next, issues
            issue_chunk_id = 0
            issue_chunk_content: list[dict[str, Any]] = []
            issue_page_generator = self.github_client.get_issues(
                repo_full_name=data.id, since=data.oldest
            )
            for issue_page in issue_page_generator:
                for issue in issue_page:
                    if len(issue_chunk_content) >= Settings.MAX_OBJECTS_IN_JOB:
                        logger.info(
                            f"Processing {len(issue_chunk_content)} issues for Github repository {data.id}..."
                        )
                        yield GithubProcessingChunk(
                            id=str(issue_chunk_id),
                            parent_group_id=data.id,
                            parent_group_raw_api_response=data.raw_api_response,
                            ts=data.oldest,
                            content_type=ContentType.ISSUE,
                            content=issue_chunk_content,
                        )
                        issue_chunk_content = []
                        issue_chunk_id += 1
                    else:
                        issue_chunk_content.append(issue)

            # Always yield remaining issues, even if less than chunk size
            if issue_chunk_content:
                logger.info(
                    f"Processing {len(issue_chunk_content)} issues for Github repository {data.id}..."
                )
                yield GithubProcessingChunk(
                    id=str(issue_chunk_id),
                    parent_group_id=data.id,
                    parent_group_raw_api_response=data.raw_api_response,
                    ts=data.oldest,
                    content=issue_chunk_content,
                    content_type=ContentType.ISSUE,
                )

        except Exception as e:
            logger.error(e)
            self.set_parent_group_data_status(
                parent_group_id=data.id, status=IntegrationStatus.FAILED
            )
            self.set_integration_status(IntegrationStatus.FAILED)
            raise

    def create_job_name(self, chunk: ProcessingChunk) -> str:
        """Create the processing job name."""
        if not isinstance(chunk, GithubProcessingChunk):
            raise Exception(
                "Chunk type for Github worker should be `GithubProcessingChunk`."
            )

        if chunk.ts:
            job_name = f"{self.integration.type}-processor-{chunk.content_type}-{chunk.k8s_parent_group_id.lower()}-{chunk.ts}-{chunk.id}"
        else:
            job_name = f"{self.integration.type}-processor-{chunk.content_type}-{chunk.k8s_parent_group_id.lower()}-{chunk.id}"
        return job_name


if __name__ == "__main__":
    container = Container()
    container.init_resources()

    # Additional environment variables
    integration_id = os.getenv("INTEGRATION_ID", None)
    if not integration_id:
        raise Exception("`INTEGRATION_ID` environment variable not defined!")

    namespace = os.getenv("NAMESPACE", None)
    if not namespace:
        raise Exception("`NAMESPACE` environment variable not defined!")

    worker = GithubWorker(
        worker_integration_id=integration_id,
        worker_namespace=namespace,
        db=container.database(),
        redis_client=container.redis_client(),
    )
    asyncio.run(worker.run())
