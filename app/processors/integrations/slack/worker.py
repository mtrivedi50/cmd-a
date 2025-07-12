import asyncio
import logging
import os
import sys
from typing import Any, Generator

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.clients.redis_client import RedisClient
from app.db.container import Container
from app.db.factory import Database
from app.db.models.choices import IntegrationStatus
from app.processors.base.types import ProcessingChunk, ProcessingParentGroupData
from app.processors.base.worker import BaseWorker
from app.processors.integrations.slack.types import SlackSecret
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


class SlackWorker(BaseWorker):
    """Worker for processing Slack channels"""

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

    def create_chunks(
        self, data: ProcessingParentGroupData
    ) -> Generator[ProcessingChunk, None, None]:
        """Process messages from a channel in chunks."""
        try:
            chunk_id = 0
            chunk_messages: list[dict[str, Any]] = []

            # Get channel history with pagination
            has_more = True
            cursor = None

            while has_more:
                response = self.slack_client.conversations_history(
                    channel=data.id,
                    cursor=cursor,
                    oldest=data.oldest,
                    limit=100,  # Max allowed by Slack API
                )
                messages = response["messages"]
                for message in messages:
                    # Skip system messages
                    if "subtype" in message:
                        continue

                    if len(chunk_messages) >= Settings.MAX_OBJECTS_IN_JOB:
                        logger.info(
                            f"Processing {len(chunk_messages)} messages for channel {data.id}..."
                        )
                        yield ProcessingChunk(
                            id=str(chunk_id),
                            parent_group_id=data.id,
                            parent_group_raw_api_response=data.raw_api_response,
                            ts=data.oldest,
                            content=chunk_messages,
                        )
                        chunk_messages = []
                        chunk_id += 1
                    else:
                        chunk_messages.append(message)

                # Handle pagination
                has_more = response["has_more"]
                if has_more:
                    cursor = response["response_metadata"].get("next_cursor")

            # Always yield remaining messages, even if less than chunk size
            if chunk_messages:
                logger.info(
                    f"Processing {len(chunk_messages)} messages for channel {data.id}..."
                )
                yield ProcessingChunk(
                    id=str(chunk_id),
                    parent_group_id=data.id,
                    parent_group_raw_api_response=data.raw_api_response,
                    ts=data.oldest,
                    content=chunk_messages,
                )

        # Raise a SlackApiError if we cannot process the messages from the channel
        except SlackApiError as slack_error:
            logger.error(
                f"Error getting channel messages: {slack_error.response['error']}"
            )
            self.set_parent_group_data_status(
                parent_group_id=data.id, status=IntegrationStatus.FAILED
            )
            self.set_integration_status(IntegrationStatus.FAILED)
            raise

        # Handle all other errors
        except Exception as e:
            logger.error(e)
            self.set_parent_group_data_status(
                parent_group_id=data.id, status=IntegrationStatus.FAILED
            )
            self.set_integration_status(IntegrationStatus.FAILED)
            raise


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

    worker = SlackWorker(
        integration_id=integration_id,
        namespace=namespace,
        db=container.database(),
        redis_client=container.redis_client(),
    )
    asyncio.run(worker.run())
