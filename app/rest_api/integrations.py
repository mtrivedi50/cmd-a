import asyncio
import json
import logging
from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from fastapi.exceptions import HTTPException
from kubernetes import config
from starlette.status import HTTP_202_ACCEPTED

from app.clients.graph_client import GraphClient
from app.clients.k8s_client import KubernetesOperator
from app.clients.vectordb_client import VectorDb
from app.db.container import Container
from app.db.factory import Database
from app.db.models.auth import User
from app.db.models.choices import ExecutionRole, KubernetesResourceType
from app.db.models.integration import (
    ChunkProcessingJob,
    Integration,
    ParentGroupData,
)
from app.db.models.k8s import K8sResource
from app.db.security import get_current_user
from app.processors.k8s_deployment import ProcessorDeployment
from app.rest_api.types.input_types import ExistingIntegrationInput, IntegrationInput
from app.rest_api.utils import (
    get_non_null_attributes_from_data,
    update_integration_status,
)
from app.settings import DeploymentMode, Settings

logger = logging.getLogger(__name__)


# Kubernetes client
config.incluster_config.load_incluster_config()


router = APIRouter()


@router.get(
    "/integration/{integration_id}", tags=["Integration"], response_model=Integration
)
@inject
async def get_integration(
    integration_id: str,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> Any:
    return db.get_object(
        Integration,
        where_conditions={
            "user": user,
            "id": integration_id,
        },
    )


@router.get("/integrations", tags=["Integration"], response_model=list[Integration])
@inject
async def list_integrations(
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> Any:
    return db.all_objects(
        Integration,
        where_conditions={
            "user": user,
        },
        order_by=["created_at"],
    )


@router.post("/integration", tags=["Integration"])
@inject
async def create_integration(
    data: IntegrationInput,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> Integration:
    # Integration db object
    integration_db_object = Integration(
        name=data.name,
        type=data.type,
        refresh_schedule=data.schedule,
        user_id=user.id,
        secret_id=data.secret_id,
    )
    db.add(integration_db_object)

    # Launch the appropriate k8s resources. Generally, integrations require two
    # resources — a scheduler and a worker. The scheduler is responsible for
    # intermittently pinging the appropriate API and adds data to the queue. It is
    # deployed as a Kubernetes CRON job. The worker is responsible for reading from the
    # queue and actually processing the data (adding to the graph database and the
    # vector database).
    image_version = (
        "__DO_NOT_EDIT__" if Settings.MODE == DeploymentMode.PROD else "latest"
    )
    deployment_manager = ProcessorDeployment(
        integration_id=str(integration_db_object.id),
        namespace=user.namespace,
        integration_type=data.type,
        scheduler_image_name="mtrivedi50/cmd-a-docling",
        scheduler_image_version=image_version,
        worker_image_name="mtrivedi50/cmd-a-docling",
        worker_image_version=image_version,
    )

    # Worker deployment
    deployment_name = deployment_manager.deploy_workers(replicas=1)
    worker_resource_db_object = K8sResource(
        execution_role=ExecutionRole.WORKER,
        resource_type=KubernetesResourceType.DEPLOYMENT,
        name=deployment_name,
        integration_id=integration_db_object.id,
    )
    db.add(worker_resource_db_object)

    # Scheduler cronjob
    cronjob_name = deployment_manager.deploy_scheduler(data.schedule)
    scheduler_resource_db_object = K8sResource(
        execution_role=ExecutionRole.SCHEDULER,
        resource_type=KubernetesResourceType.CRON_JOB,
        name=cronjob_name,
        integration_id=integration_db_object.id,
    )
    db.add(scheduler_resource_db_object)
    return integration_db_object


@router.patch(
    "/integration/{integration_id}", tags=["Integration"], response_model=Integration
)
@inject
async def update_integration(
    integration_id: str,
    data: ExistingIntegrationInput,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> Any:
    non_null_attributes = get_non_null_attributes_from_data(data)
    integration_obj = db.update_object(
        db_type=Integration,
        where_conditions={
            "id": integration_id,
            "user": user,
        },
        **non_null_attributes,
    )

    # If we have paused the integration, we need to pause our worker deployment. Let the
    # current processing jobs finish.
    operator = KubernetesOperator()
    if data.is_active is not None:
        # If deployment is active, then re-create the worker and scheduler. This will
        # raise an error if they already exist, because if the user is submitting a
        # PATCH to activate an integration, then it should have been inactive before.
        if data.is_active:
            image_version = (
                "__DO_NOT_EDIT__" if Settings.MODE == DeploymentMode.PROD else "latest"
            )
            deployment_manager = ProcessorDeployment(
                integration_id=str(integration_obj.id),
                namespace=user.namespace,
                integration_type=integration_obj.type,
                scheduler_image_name="mtrivedi50/cmd-a-docling",
                scheduler_image_version=image_version,
                worker_image_name="mtrivedi50/cmd-a-docling",
                worker_image_version=image_version,
            )
            deployment_manager.deploy_workers(replicas=1)
            deployment_manager.deploy_scheduler(integration_obj.refresh_schedule)

        # Otherwise, delete the deployment and scheduler. Note that this doesn't delete
        # the queue, so when the resources are created again, it should pick up where it
        # left off.
        else:
            deployment_name = operator.create_resource_name(
                integration_type=integration_obj.type,
                execution_role=ExecutionRole.WORKER,
                resource_type=KubernetesResourceType.DEPLOYMENT,
            )
            cronjob_name = operator.create_resource_name(
                integration_type=integration_obj.type,
                execution_role=ExecutionRole.SCHEDULER,
                resource_type=KubernetesResourceType.CRON_JOB,
            )
            operator.destroy_deployment(
                namespace=user.namespace,
                deployment_name=deployment_name,
                async_req=True,
            )
            operator.destroy_cronjob(
                namespace=user.namespace,
                cronjob_name=cronjob_name,
                async_req=True,
            )

    return integration_obj


@router.delete("/integration/{integration_id}", tags=["Integration"])
@inject
def delete_integration(
    integration_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
    graph_client: GraphClient = Depends(Provide[Container.graph_client]),
    vector_db: VectorDb = Depends(Provide[Container.vector_db]),
) -> dict[str, int | str]:
    with db.session() as session:
        integration = db.get_object(
            db_type=Integration,
            where_conditions={"id": integration_id},
            session=session,
        )
        if integration.user_id != user.id:
            raise HTTPException(
                status_code=404,
                detail=f"Cannot delete integration `{integration_id}`, you are not the owner!",
            )

        # Otherwise, delete the integration
        k8s_operator = KubernetesOperator()
        for k8s_resource in integration.k8s_resources:
            # For mypy
            if not isinstance(k8s_resource, K8sResource):
                raise HTTPException(
                    status_code=404,
                    detail=f"Unknown K8sResource type `{type(k8s_resource)}`",
                )
            if k8s_resource.resource_type == KubernetesResourceType.DEPLOYMENT:
                k8s_operator.destroy_deployment(
                    namespace=user.namespace,
                    deployment_name=k8s_resource.name,
                    async_req=True,
                )
            elif k8s_resource.resource_type == KubernetesResourceType.CRON_JOB:
                k8s_operator.destroy_cronjob(
                    namespace=user.namespace,
                    cronjob_name=k8s_resource.name,
                    async_req=True,
                )

            # No need to explicitly delete the database object. This is handled by our
            # cascade relationship.

        # Delete all jobs
        background_tasks.add_task(
            k8s_operator.async_delete_jobs,
            namespace=user.namespace,
            pattern=f"{integration.type}-processor",
        )
        background_tasks.add_task(
            k8s_operator.async_delete_cron_jobs,
            namespace=user.namespace,
            pattern=f"{integration.type}-processor",
        )
        background_tasks.add_task(
            k8s_operator.async_delete_pods,
            namespace=user.namespace,
            pattern=f"{integration.type}-processor",
        )

        # Delete graph and vector data. This is asynchornous
        background_tasks.add_task(graph_client.delete_integration, integration_id)
        background_tasks.add_task(
            vector_db.delete_integration,
            namespace=user.namespace,
            integration_id=integration_id,
        )

        db.delete(integration)
    return {
        "status_code": HTTP_202_ACCEPTED,
        "detail": f"Integration `{integration_id}` successfully deleted!",
    }


@router.get(
    "/parent-group/{integration_id}",
    tags=["Integration"],
    response_model=list[ParentGroupData],
)
@inject
async def get_parent_groups(
    integration_id: str,
    page: int,
    size: int,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> list[Any]:
    return db.paginated_objects(
        db_type=ParentGroupData,
        order_by=["name"],
        page=page,
        size=size,
        where_conditions={
            "integration_id": integration_id,
        },
    )


@router.get(
    "/processing-jobs/{integration_id}",
    tags=["Integration"],
    response_model=dict[str, list[ChunkProcessingJob]],
)
@inject
async def get_processing_jobs(
    integration_id: str,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> dict[str, Any]:
    parent_groups = db.all_objects(
        db_type=ParentGroupData,
        where_conditions={
            "integration_id": integration_id,
        },
    )
    parent_group_jobs_mapping: dict[str, list[ChunkProcessingJob]] = {}
    for pg in parent_groups:
        jobs = db.all_objects(
            db_type=ChunkProcessingJob,
            where_conditions={"parent_group_id": pg.parent_group_id},
        )
        parent_group_jobs_mapping[pg.parent_group_id] = jobs
    return parent_group_jobs_mapping


@router.websocket("/ws/")
@inject
async def integration_parent_group_data_status(
    websocket: WebSocket,
    db: Database = Depends(Provide[Container.database]),
):
    subscribed_to_integrations: set[str] = set()
    deleted_integrations: set = set()
    await websocket.accept()
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
                if not data:
                    continue
                new_integration_id = data.get("integration_id")
                if not new_integration_id:
                    await websocket.send_json({"error": "integration_id is required"})
                    continue
                subscribed_to_integrations.add(new_integration_id)

            # No data, just pass. Do not block the status checks for subscribed
            # integrations.
            except asyncio.TimeoutError:
                pass

            # If we have not subscribed to any integrations, continue
            if not subscribed_to_integrations:
                continue

            # Otherwise, check the status of all and send to the client.
            updated_objects: dict[str, dict[str, Any]] = {}
            for integration_id in subscribed_to_integrations:
                # If the integration no longer exists, remove it from our
                # subscribed_to_integrations list and continue.
                try:
                    db.get_object(
                        db_type=Integration, where_conditions={"id": integration_id}
                    )
                except HTTPException:
                    deleted_integrations.add(integration_id)
                    continue

                # Check integration and parent group statuses
                user = db.get_object_fk_attribute(
                    db_type=Integration,
                    where_conditions={
                        "id": integration_id,
                    },
                    fk="user",
                    fk_type=User,
                )
                updated_objs = update_integration_status(
                    integration_id=integration_id, namespace=user.namespace, db=db
                )

                # Hack-y approach for serializing UUIDs
                updated_objs_json = json.loads(updated_objs.model_dump_json())
                updated_objects[integration_id] = updated_objs_json

            # Delete integrations
            for integration_id in deleted_integrations:
                if integration_id in subscribed_to_integrations:
                    subscribed_to_integrations.remove(integration_id)

            # Send status update
            await websocket.send_json(updated_objects)

            # Add a small delay to prevent overwhelming the server
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()
