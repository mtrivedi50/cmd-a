import logging
import os
import sys

from fastapi import HTTPException

from app.clients.redis_client import RedisClient
from app.db.container import Container
from app.db.factory import Database
from app.db.models.choices import IntegrationStatus, ParentGroupDataType
from app.db.models.integration import ParentGroupData
from app.processors.base.scheduler import BaseScheduler
from app.processors.base.types import ProcessingParentGroupData
from app.processors.integrations.github.api import GithubClient
from app.processors.integrations.github.types import GithubSecret

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Send logs to stdout
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class GithubScheduler(BaseScheduler):
    """
    Intermittently reads data GitHub repositories channels and adds them to Redis
    queue. Deployed via a Kubernetes CronJob.
    """

    github_secret: GithubSecret
    github_client: GithubClient

    def __init__(
        self,
        *,
        scheduler_integration_id: str,
        scheduler_namespace: str,
        db: Database,
        redis_client: RedisClient,
    ):
        super().__init__(
            integration_id=scheduler_integration_id,
            namespace=scheduler_namespace,
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

    def get_parent_groups(self) -> list[ProcessingParentGroupData]:
        """
        Retrieve GitHub repositories using PyGithub.
        """
        try:
            # Get all repositories. We will only parse code changes / issues that have
            # happened since the integration's `last_run`.
            repositories = self.github_client.get_repos()

            # Create ProcessingParentGroupData model instance and database object
            parent_group_data = []
            for repo in repositories:
                # Database object
                try:
                    parent_group_data_obj = self.db.get_object(
                        db_type=ParentGroupData,
                        where_conditions={
                            "parent_group_id": repo["full_name"],
                            "integration_id": self.integration_id,
                        },
                    )
                except HTTPException:
                    parent_group_data_obj = ParentGroupData(
                        parent_group_id=repo["full_name"],
                        name=repo["full_name"],
                        type=ParentGroupDataType.GITHUB_REPO,
                        status=IntegrationStatus.NOT_STARTED,
                        integration=self.integration,
                    )
                    self.db.add(parent_group_data_obj)

                # Model instance. This is what is actually queued. Only requeue the
                # parent group it is failed or succeeded previously.
                parent_group_last_run = (
                    None
                    if parent_group_data_obj.last_run is None
                    else str(parent_group_data_obj.last_run.timestamp())
                )
                if (
                    parent_group_data_obj.last_run is None
                    or parent_group_data_obj.status is None
                    or parent_group_data_obj.status
                    in [IntegrationStatus.SUCCESS, IntegrationStatus.FAILED]
                ):
                    parent_group_data.append(
                        ProcessingParentGroupData(
                            integration_id=self.integration_id,
                            namespace=self.namespace,
                            type=ParentGroupDataType.GITHUB_REPO,
                            id=repo["full_name"],
                            oldest=parent_group_last_run,
                            raw_api_response=repo,
                        )
                    )
            return parent_group_data

        except Exception as e:
            logger.error(f"Error retrieving GitHub repositories: {e}")
            raise

    def get_parent_group_data_name(self, data: ProcessingParentGroupData) -> str:
        return data.raw_api_response["full_name"]


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

    # Start main scheduling loop
    scheduler = GithubScheduler(
        scheduler_integration_id=integration_id,
        scheduler_namespace=namespace,
        db=container.database(),
        redis_client=container.redis_client(),
    )
    scheduler.run()
