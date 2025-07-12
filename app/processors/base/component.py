import logging
import sys
from abc import ABC
from datetime import datetime

from app.clients.k8s_client import KubernetesOperator
from app.clients.redis_client import RedisClient
from app.db.factory import Database
from app.db.models.choices import IntegrationStatus
from app.db.models.integration import Integration, ParentGroupData
from app.db.models.k8s import Secret

# Logger
logging.basicConfig()
logger = logging.getLogger(__name__)

# Send logs to stdout
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class BaseProcessingComponent(KubernetesOperator, ABC):
    """
    Base class that defines some common logic used throughout our processor services
    (e.g., CRON jobs, deployments, jobs).
    """

    db: Database
    redis_client: RedisClient
    integration_id: str
    namespace: str
    integration: Integration
    integration_secret: Secret

    def __init__(
        self,
        *,
        integration_id: str,
        namespace: str,
        db: Database,
        redis_client: RedisClient,
    ):
        super().__init__()

        self.db = db
        self.redis_client = redis_client
        self.integration_id = integration_id
        self.namespace = namespace

        # Database objects
        with self.db.session() as session:
            # Run for all integrations
            integration = db.get_object(
                db_type=Integration,
                where_conditions={"id": self.integration_id},
                session=session,
            )
            if integration.user.namespace != self.namespace:
                raise Exception(
                    f"Tried retrieving data from user in namespace `{integration.user.namespace}`! This indicates leakage in the underlying Kubernetes architecture."
                )
            self.integration = integration
            self.integration_secret = integration.secret

    def update_integration_status_last_run(self) -> None:
        """Update Integration `last_run` and `status` fields. This is used when the
        scheduler has scheduled all of the integration's parent data groups (e.g., all
        Slack channels have been queued).
        """
        with self.db.session() as session:
            integration = self.db.get_object(
                db_type=Integration,
                where_conditions={"id": self.integration_id},
                session=session,
            )
            integration.last_run = datetime.now()
            integration.status = IntegrationStatus.RUNNING
            session.commit()
            session.refresh(integration)

    def set_integration_status(self, status: IntegrationStatus) -> None:
        """Update Integration `status` field. This is generally used to set the
        integration status to FAILED or SUCCESS."""
        with self.db.session() as session:
            integration = self.db.get_object(
                db_type=Integration,
                where_conditions={"id": self.integration_id},
                session=session,
            )
            integration.status = status
            session.commit()
            session.refresh(integration)

    def set_parent_group_data_status(
        self, parent_group_id: str, status: IntegrationStatus
    ) -> None:
        with self.db.session() as session:
            parent_group_data = self.db.get_object(
                db_type=ParentGroupData,
                where_conditions={
                    "parent_group_id": parent_group_id,
                    "integration_id": self.integration_id,
                },
                session=session,
            )
            parent_group_data.last_run = datetime.now()
            parent_group_data.status = status
            session.commit()
            session.refresh(parent_group_data)
