import asyncio
import json
import logging
import sys
import time
from abc import abstractmethod
from datetime import datetime
from typing import Generator
from uuid import uuid4

from kubernetes import client

from app.db.models.choices import IntegrationStatus
from app.db.models.integration import ChunkProcessingJob, ParentGroupData
from app.processors.base.component import BaseProcessingComponent
from app.processors.base.types import ProcessingChunk, ProcessingParentGroupData
from app.processors.utils import create_job_input_redis_key
from app.settings import DeploymentMode, PostgresDatabaseConfig, Settings

# Logging
logging.basicConfig()
logger = logging.getLogger(__name__)

# Send logs to stdout
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class BaseWorker(BaseProcessingComponent):
    """Base class for all integration workers"""

    async def run(self) -> None:
        """Main worker loop"""
        # We handle errors in the child class function implementations.
        while True:
            # Cap the number of processing jobs. We automatically delete jobs that have
            # succeeded in our Websocket endpoint, so this will mostly be running or
            # queued jobs.
            jobs = self.get_jobs_matching_pattern(
                namespace=self.namespace, pattern=f"{self.integration.type}-processor-"
            )
            if len(list(jobs.keys())) > Settings.MAX_PROCESSING_JOBS:
                await asyncio.sleep(10)
                continue
            else:
                parent_group_data_from_queue = self.get_next_queued_item()
                if parent_group_data_from_queue:
                    self.process_queued_data(parent_group_data_from_queue)

                await asyncio.sleep(10)

    def get_next_queued_item(self) -> ProcessingParentGroupData | None:
        """Get next item from Redis queue"""
        try:
            # Use BLPOP to block until an item is available
            queue_key = f"queue:{self.integration.type}:{self.integration_id}"
            result = self.redis_client.simple_brpop(
                queue_key, timeout=Settings.QUEUE_TIMEOUT
            )
            if result:
                parent_group_data = ProcessingParentGroupData(**json.loads(result[1]))
                if parent_group_data.namespace != self.namespace:
                    raise Exception(
                        f"Tried retrieving data from user in namespace `{parent_group_data.namespace}`! This indicates leakage in the underlying Kubernetes architecture."
                    )
                return parent_group_data
            return None

        except Exception as e:
            logger.error(f"Error getting next queued item: {e}")
            self.set_integration_status(IntegrationStatus.FAILED)
            raise

    @abstractmethod
    def create_chunks(
        self, data: ProcessingParentGroupData
    ) -> Generator[ProcessingChunk, None, None]:
        """Split parent group data into chunks for processing"""
        pass

    def create_job_name(self, chunk: ProcessingChunk) -> str:
        """Create the processing job name."""
        if chunk.ts:
            job_name = f"{self.integration.type}-processor-{chunk.k8s_parent_group_id.lower()}-{chunk.ts}-{chunk.id}"
        else:
            job_name = f"{self.integration.type}-processor-{chunk.k8s_parent_group_id.lower()}-{chunk.id}"
        return job_name

    def launch_processing_job(self, chunk: ProcessingChunk) -> client.V1Job:
        """Launch a job to process a chunk of messages"""
        batch_api = client.BatchV1Api()
        job_name = self.create_job_name(chunk)

        # Store the chunk data in Redis. The chunk processor job will read the chunk
        # data from Redis. This helps us avoid storing the chunk data (which could be
        # quite large) in an environment variable.
        redis_key = create_job_input_redis_key(self.namespace, job_name)
        self.redis_client.simple_set(redis_key, chunk.model_dump_json())

        if not isinstance(Settings.DB, PostgresDatabaseConfig):
            raise Exception("Kubernetes development requires a Postgres database!")

        # Create job specification. A few notes:
        #   1. The slack-processer image is created via the
        #      integrations.src.slack.processor.SlackMessageProcessor class.
        #   2. We use environment variables to communicate the chunk data because it's
        #      slightly easier than using CLI arguments.
        job_uuid = uuid4()
        env_vars = [
            client.V1EnvVar(name="JOB_ID", value=str(job_uuid)),
            client.V1EnvVar(
                name="CHUNK_DATA_KEY",
                value=redis_key,
            ),
            client.V1EnvVar(
                name="INTEGRATION_ID",
                value=self.integration_id,
            ),
            client.V1EnvVar(
                name="NAMESPACE",
                value=self.namespace,
            ),
        ] + self.create_env_vars_from_settings()

        image_version = (
            "__DO_NOT_EDIT__" if Settings.MODE == DeploymentMode.PROD else "latest"
        )
        job = client.V1Job(
            metadata=client.V1ObjectMeta(name=job_name, namespace=self.namespace),
            spec=client.V1JobSpec(
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name=f"{self.integration.type}-processor",
                                image=f"mtrivedi50/cmd-a-docling:{image_version}",
                                command=[
                                    "uv",
                                    "run",
                                    "python",
                                    "-m",
                                    f"app.processors.integrations.{self.integration.type}.processor",
                                ],
                                env=env_vars,
                                image_pull_policy="Always"
                                if Settings.MODE == DeploymentMode.PROD
                                else "Never",
                            )
                        ],
                        restart_policy="Never",
                    )
                ),
                backoff_limit=3,
            ),
        )

        try:
            batch_api.create_namespaced_job(namespace=self.namespace, body=job)
            time.sleep(1)

            # Create database object. We want to pass this job ID to the processor so
            # that the processor can update its own status.
            job_db = ChunkProcessingJob(
                id=job_uuid,
                name=job_name,
                status=IntegrationStatus.NOT_STARTED,
                parent_group_id=chunk.parent_group_id,
            )
            self.db.add(job_db)

        except Exception as e:
            logger.error(f"Error creating job for chunk {chunk.id}: {str(e)}")
            raise

        return job

    def process_queued_data(
        self, data: ProcessingParentGroupData
    ) -> list[client.V1Job]:
        """Process queued data by creating chunks and launching jobs"""
        jobs: list[client.V1Job] = []
        flag_has_chunks = False
        for chunk in self.create_chunks(data):
            flag_has_chunks = True

            # For mypy
            if not isinstance(chunk, ProcessingChunk):
                # Set parent group and integration status to FAILED. We update the
                # integration status based on the statuses of all associated parent
                # groups via a Websocket.
                self.set_parent_group_data_status(
                    parent_group_id=data.id, status=IntegrationStatus.FAILED
                )
                raise Exception(
                    f"Unexpected type for chunk: {chunk.__class__.__name__}"
                )

            # Launch processing job. We will use a Websocket to get the status of these
            # jobs.
            job = self.launch_processing_job(chunk)
            jobs.append(job)

        # If the parent group has chunks, then change the status to RUNNING. Otherwise,
        # change the status to SUCCESS.
        self.db.update_object(
            db_type=ParentGroupData,
            where_conditions={"parent_group_id": data.id},
            headers=None,
            status=IntegrationStatus.RUNNING
            if flag_has_chunks
            else IntegrationStatus.SUCCESS,
            last_run=datetime.now(),
        )
        return jobs
