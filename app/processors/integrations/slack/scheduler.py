import logging
import os
import sys

from fastapi import HTTPException
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.clients.redis_client import RedisClient
from app.db.container import Container
from app.db.factory import Database
from app.db.models.choices import IntegrationStatus, ParentGroupDataType
from app.db.models.integration import ParentGroupData
from app.processors.base.scheduler import BaseScheduler
from app.processors.base.types import ProcessingParentGroupData
from app.processors.integrations.slack.types import SlackSecret

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Send logs to stdout
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class SlackScheduler(BaseScheduler):
    """
    Intermittently reads messages Slack channels and adds them to Redis queue. Deployed
    via a Kubernetes CronJob
    """

    slack_secret: SlackSecret
    slack_client: WebClient

    def __init__(
        self,
        *,
        integration_id: str,
        namespace: str,
        db: Database,
        redis_client: RedisClient,
    ):
        super().__init__(
            integration_id=integration_id,
            namespace=namespace,
            db=db,
            redis_client=redis_client,
        )

        # Slack client
        token_data = self.read_namespaced_secret(
            namespace=self.namespace,
            secret_name=self.integration_secret.slug,
        )
        self.slack_secret = SlackSecret(**token_data)
        self.slack_client = WebClient(token=self.slack_secret.token)

    def get_parent_groups(self):
        """Get active Slack channels that need processing"""
        parent_groups: list[ProcessingParentGroupData] = []

        # Grab all channels. For each channel, we will grab messages in between now and
        # when the channel was last processed.
        try:
            response = self.slack_client.conversations_list(
                types=["public_channel", "private_channel"], exclude_archived=True
            )
        except SlackApiError as e:
            logger.error(f"Error listing channels: {e.response['error']}")
            raise

        for channel in response["channels"]:
            # Add database object
            try:
                parent_group_data_obj = self.db.get_object(
                    db_type=ParentGroupData,
                    where_conditions={
                        "parent_group_id": channel["id"],
                        "integration_id": self.integration_id,
                    },
                )
            except HTTPException:
                parent_group_data_obj = ParentGroupData(
                    parent_group_id=channel["id"],
                    name=channel["name"],
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
                parent_group = ProcessingParentGroupData(
                    integration_id=self.integration_id,
                    namespace=self.namespace,
                    type=ParentGroupDataType.SLACK_CHANNEL,
                    id=channel["id"],
                    oldest=parent_group_last_run,
                    raw_api_response=channel,
                )
                parent_groups.append(parent_group)

        return parent_groups

    def get_parent_group_data_name(self, data: ProcessingParentGroupData) -> str:
        return data.raw_api_response["name"]


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
    scheduler = SlackScheduler(
        integration_id=integration_id,
        namespace=namespace,
        db=container.database(),
        redis_client=container.redis_client(),
    )
    scheduler.run()
