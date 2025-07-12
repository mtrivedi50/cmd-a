import json
import logging
import sys
from abc import abstractmethod
from datetime import datetime

from app.db.models.choices import IntegrationStatus
from app.db.models.integration import Integration, ParentGroupData
from app.processors.base.component import BaseProcessingComponent
from app.processors.base.types import ProcessingParentGroupData

# Logging
logging.basicConfig()
logger = logging.getLogger(__name__)

# Send logs to stdout
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class BaseScheduler(BaseProcessingComponent):
    """Base class for all integration schedulers"""

    @abstractmethod
    def get_parent_groups(self) -> list[ProcessingParentGroupData]:
        """Get parent group data to add to queue"""
        pass

    @abstractmethod
    def get_parent_group_data_name(self, data: ProcessingParentGroupData) -> str:
        """
        Get the name for each parent group. Make this an abstract method that is
        implemented by each child class so that we can handle different API response
        formats.
        """
        pass

    def add_to_queue(self, data: ProcessingParentGroupData) -> None:
        """Add parent group data to Redis queue"""
        queue_key = f"queue:{self.integration.type}:{self.integration_id}"
        logger.info(f"Adding {data._pretty_type} {data.id} to queue")
        self.redis_client.simple_lpush(queue_key, data.model_dump_json())

    def enqueue_parent_groups(self):
        """Get all active parent groups that need to be processed"""
        parent_groups = self.get_parent_groups()
        for group in parent_groups:
            self.add_to_queue(group)

            # Update the parent group's status
            self.db.update_object(
                db_type=ParentGroupData,
                where_conditions={
                    "parent_group_id": group.id,
                    "integration_id": self.integration_id,
                },
                status=IntegrationStatus.QUEUED,
            )

        # Update integration last_run and status. We update the integration's `last_run`
        # when the integration's parent groups are added to the queue. We update each
        # parent group's `last_run` when all of their processing jobs have been kicked
        # off.
        self.db.update_object(
            db_type=Integration,
            where_conditions={
                "id": self.integration_id,
            },
            headers=None,
            status=IntegrationStatus.QUEUED,
            last_run=datetime.now(),
        )

    def run(self) -> None:
        """Main scheduling loop"""
        try:
            self.enqueue_parent_groups()
        except Exception as e:
            error_json = {
                "integration_id": self.integration_id,
                "namespace": self.namespace,
                "detail": str(e),
            }
            logger.error(f"Scheduler error: {json.dumps(error_json)}")
            raise
