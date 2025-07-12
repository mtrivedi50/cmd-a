"""
Manages deployment of Slack processing components on Kubernetes.
"""
import logging
from datetime import datetime
from typing import Any

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from app.clients.k8s_client import KubernetesOperator
from app.db.models.choices import ExecutionRole, IntegrationType, KubernetesResourceType
from app.settings import DeploymentMode, Settings

logger = logging.getLogger(__name__)


class ProcessorDeployment(KubernetesOperator):
    integration_id: str
    namespace: str
    integration_type: IntegrationType
    scheduler_image_name: str
    scheduler_image_version: str
    scheduler_resource_requests: dict[str, str]
    scheduler_resource_limits: dict[str, str]
    worker_image_name: str
    worker_image_version: str
    worker_resource_requests: dict[str, str]
    worker_resource_limits: dict[str, str]

    scheduler_resource_requirements: client.V1ResourceRequirements
    worker_resource_requirements: client.V1ResourceRequirements

    def __init__(
        self,
        *,
        integration_id: str,
        namespace: str,
        integration_type: IntegrationType,
        scheduler_image_name: str,
        scheduler_image_version: str = "latest",
        scheduler_resource_requests: dict[str, str] = {
            "cpu": "100m",
            "memory": "256Mi",
        },
        scheduler_resource_limits: dict[str, str] = {"cpu": "200m", "memory": "512Mi"},
        worker_image_name: str,
        worker_image_version: str = "latest",
        worker_resource_requests: dict[str, str] = {"cpu": "200m", "memory": "512Mi"},
        worker_resource_limits: dict[str, str] = {"cpu": "500m", "memory": "1Gi"},
    ):
        super().__init__()

        # Generally, processors require two resources — a scheduler and a worker. The
        # scheduler is responsible for intermittently pinging the appropriate API and adds
        # data to the queue. It is deployed as a Kubernetes CRON job. The worker is
        # responsible for reading from the queue and actually processing the data (adding to
        # the graph database and the vector database).
        self.integration_id = integration_id
        self.namespace = namespace
        self.integration_type = integration_type
        self.scheduler_image_name = scheduler_image_name
        self.scheduler_image_version = scheduler_image_version
        self.scheduler_resource_requests = scheduler_resource_requests
        self.scheduler_resource_limits = scheduler_resource_limits
        self.worker_image_name = worker_image_name
        self.worker_image_version = worker_image_version
        self.worker_resource_requests = worker_resource_requests
        self.worker_resource_limits = worker_resource_limits

        self.scheduler_resource_requirements = client.V1ResourceRequirements(
            requests=self.scheduler_resource_requests,
            limits=self.scheduler_resource_limits,
        )
        self.worker_resource_requirements = client.V1ResourceRequirements(
            requests=self.worker_resource_requests, limits=self.worker_resource_limits
        )

    def create_env_var_list(self) -> list[client.V1EnvVar]:
        # Integration ID
        integration_id = client.V1EnvVar(
            name="INTEGRATION_ID",
            value=self.integration_id,
        )
        # Namespace
        namespace = client.V1EnvVar(
            name="NAMESPACE",
            value=self.namespace,
        )

        # Environment variables from settings
        env_vars_from_settings = self.create_env_vars_from_settings()

        return [
            integration_id,
            namespace,
        ] + env_vars_from_settings

    def deploy_scheduler(self, schedule: str = "0 * * * *") -> str:
        """
        Deploy the Slack scheduler CronJob
        """
        cronjob_name = self.create_resource_name(
            integration_type=self.integration_type,
            execution_role=ExecutionRole.SCHEDULER,
            resource_type=KubernetesResourceType.CRON_JOB,
        )
        container_name = self.create_integration_execution_role_name(
            self.integration_type, ExecutionRole.SCHEDULER
        )

        # Environment variables
        try:
            cron_job = client.V1CronJob(
                metadata=self.create_main_resource_metadata(
                    namespace=self.namespace,
                    resource_name=cronjob_name,
                ),
                spec=client.V1CronJobSpec(
                    schedule=schedule,  # defaults to hourly
                    concurrency_policy="Forbid",
                    job_template=client.V1JobTemplateSpec(
                        spec=client.V1JobSpec(
                            template=client.V1PodTemplateSpec(
                                spec=client.V1PodSpec(
                                    containers=[
                                        client.V1Container(
                                            name=container_name,
                                            image=f"{self.scheduler_image_name}:{self.scheduler_image_version}",
                                            command=[
                                                "uv",
                                                "run",
                                                "python",
                                                "-m",
                                                f"app.processors.integrations.{self.integration_type}.scheduler",
                                            ],
                                            # resources=self.scheduler_resource_requirements,
                                            env=self.create_env_var_list(),
                                            image_pull_policy="Always"
                                            if Settings.MODE == DeploymentMode.PROD
                                            else "Never",
                                        )
                                    ],
                                    restart_policy="OnFailure",
                                )
                            )
                        )
                    ),
                ),
            )

            # Create or update the CronJob
            try:
                self.batch_api.create_namespaced_cron_job(
                    namespace=self.namespace, body=cron_job
                )
                logger.info("Created Slack scheduler CronJob")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    self.batch_api.patch_namespaced_cron_job(
                        name=cronjob_name, namespace=self.namespace, body=cron_job
                    )
                    logger.info("Updated Slack scheduler CronJob")
                else:
                    raise

            # We verify the Cronjob elsewhere. Return just the name
            return cronjob_name

        except Exception as e:
            logger.error(f"Failed to deploy Slack scheduler: {str(e)}")
            raise

    def deploy_workers(self, replicas: int = 3) -> str:
        """Deploy Slack worker deployment"""
        deployment_name = self.create_resource_name(
            integration_type=self.integration_type,
            execution_role=ExecutionRole.WORKER,
            resource_type=KubernetesResourceType.DEPLOYMENT,
        )
        labels = self.create_deployment_label_selector(
            integration_type=self.integration_type, execution_role=ExecutionRole.WORKER
        )
        container_name = self.create_integration_execution_role_name(
            self.integration_type, ExecutionRole.WORKER
        )
        try:
            deployment = client.V1Deployment(
                metadata=self.create_main_resource_metadata(
                    self.namespace, deployment_name
                ),
                spec=client.V1DeploymentSpec(
                    replicas=replicas,
                    selector=client.V1LabelSelector(match_labels=labels),
                    template=client.V1PodTemplateSpec(
                        metadata=client.V1ObjectMeta(labels=labels),
                        spec=client.V1PodSpec(
                            containers=[
                                client.V1Container(
                                    name=container_name,
                                    image=f"{self.worker_image_name}:{self.worker_image_version}",
                                    # resources=self.worker_resource_requirements,
                                    command=[
                                        "uv",
                                        "run",
                                        "python",
                                        "-m",
                                        f"app.processors.integrations.{self.integration_type}.worker",
                                    ],
                                    env=self.create_env_var_list(),
                                    image_pull_policy="Always"
                                    if Settings.MODE == DeploymentMode.PROD
                                    else "Never",
                                )
                            ]
                        ),
                    ),
                ),
            )

            # Create or update the Deployment
            try:
                self.apps_api.create_namespaced_deployment(
                    namespace=self.namespace, body=deployment
                )
                logger.info("Created Slack workers deployment")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    self.apps_api.patch_namespaced_deployment(
                        name=deployment_name, namespace=self.namespace, body=deployment
                    )
                    logger.info("Updated Slack workers deployment")
                else:
                    raise

            # We verify the deployment later. For now, return the name
            return deployment_name

        except Exception as e:
            logger.error(f"Failed to deploy Slack workers: {str(e)}")
            raise

    async def check_health(self) -> dict[str, Any]:
        """
        Check health of all Slack processing components.
        """
        cronjob_name = self.create_resource_name(
            self.integration_type,
            ExecutionRole.SCHEDULER,
            KubernetesResourceType.CRON_JOB,
        )
        deployment_name = self.create_resource_name(
            self.integration_type,
            ExecutionRole.WORKER,
            KubernetesResourceType.DEPLOYMENT,
        )
        try:
            # Check CronJob
            cronjob_status = "unknown"
            cronjob_last_schedule_time: datetime | None = None
            try:
                cronjob = self.batch_api.read_namespaced_cron_job(
                    name=cronjob_name, namespace=self.namespace
                )
                if cronjob.status and cronjob.status.last_schedule_time:
                    cronjob_status = "healthy"
                    cronjob_last_schedule_time = cronjob.status.last_schedule_time
                else:
                    cronjob_status = "not_scheduled"
            except ApiException:
                cronjob_status = "not_found"

            # Check Workers
            worker_status = "unknown"
            ready_replicas: int | None = None
            desired_replicas: int | None = None
            try:
                deployment = self.apps_api.read_namespaced_deployment_status(
                    name=deployment_name, namespace=self.namespace
                )
                if (
                    deployment.status
                    and deployment.status.ready_replicas
                    and deployment.spec
                    and deployment.status.ready_replicas == deployment.spec.replicas
                ):
                    worker_status = "healthy"
                    ready_replicas = deployment.status.ready_replicas
                    desired_replicas = deployment.spec.replicas
                else:
                    worker_status = "degraded"
            except ApiException:
                worker_status = "not_found"

            return {
                "scheduler": {
                    "status": cronjob_status,
                    "last_schedule": cronjob_last_schedule_time,
                },
                "workers": {
                    "status": worker_status,
                    "ready_replicas": ready_replicas,
                    "desired_replicas": desired_replicas,
                },
            }

        except Exception as e:
            logger.error(f"Error checking component health: {str(e)}")
            return {"scheduler": {"status": "error"}, "workers": {"status": "error"}}
