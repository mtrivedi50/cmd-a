from typing import Any, TypeVar

from pydantic import BaseModel

from app.clients.k8s_client import KubernetesOperator
from app.db.factory import Database
from app.db.models.choices import IntegrationStatus
from app.db.models.integration import ChunkProcessingJob, Integration, ParentGroupData
from app.rest_api.types.response_model_types import UpdatedIntegrationParentGroups

T = TypeVar("T", bound=BaseModel)


def update_parent_group_status(
    parent_group_id: str,
    namespace: str,
    db: Database,
) -> ParentGroupData:
    """
    Each parent group has a number of chunk processing jobs. The status of the parent
    group is directly tied to the status of these jobs. If any of the jobs has failed,
    then the parent group has failed. If any of the jobs is running, then the parent
    group is running. If all the jobs have succeeded, then the parent group has
    succeeded.
    """
    operator = KubernetesOperator()
    jobs = db.all_objects(
        db_type=ChunkProcessingJob,
        where_conditions={
            "parent_group_id": parent_group_id,
        },
    )

    # If there are no jobs, then just return the status of the parent group. It's either
    # `NOT_STARTED` or `QUEUED`
    if not jobs:
        return db.get_object(
            db_type=ParentGroupData,
            where_conditions={"parent_group_id": parent_group_id},
        )

    job_statuses: list[IntegrationStatus] = []
    for job in jobs:
        # Only check the job status if it's not `SUCCESS`. Once it's `SUCCESS`, we
        # delete the job from our cluster.
        if job.status != IntegrationStatus.SUCCESS:
            status = operator.check_job_status(namespace=namespace, job_name=job.name)
            db.update_object(
                db_type=ChunkProcessingJob,
                where_conditions={"name": job.name, "parent_group_id": parent_group_id},
                headers=None,
                status=status,
            )
        else:
            status = job.status

            # Delete the job from our cluster. The job's database status will already be
            # `SUCCESS`, so no need to set it here.
            operator.async_delete_jobs(
                namespace=namespace,
                pattern=job.name,
            )
            operator.async_delete_pods(
                namespace=namespace,
                pattern=job.name,
            )

        job_statuses.append(status)

    # Parent group status
    if any([status == IntegrationStatus.FAILED for status in job_statuses]):
        pg_status = IntegrationStatus.FAILED
    elif any([status == IntegrationStatus.RUNNING for status in job_statuses]):
        pg_status = IntegrationStatus.RUNNING
    elif all([status == IntegrationStatus.SUCCESS for status in job_statuses]):
        pg_status = IntegrationStatus.SUCCESS
    else:
        raise Exception(
            f"Unknown parent group status! Job names are: {[job.name for job in jobs]}, and statuses are {job_statuses}."
        )
    return db.update_object(
        db_type=ParentGroupData,
        where_conditions={
            "parent_group_id": parent_group_id,
        },
        status=pg_status,
    )


def update_integration_status(
    integration_id: str,
    namespace: str,
    db: Database,
) -> UpdatedIntegrationParentGroups:
    """
    Each integration has several parent groups. The status of the integration is
    directly tied to the status of the parent groups. If any of the parent groups has
    failed, then the integration has failed. If any of the parent groups is running,
    then the integration is running. If all of the parent groups have succeeded, then
    the integration has succeeded.
    """
    parent_groups = db.all_objects(
        db_type=ParentGroupData, where_conditions={"integration_id": integration_id}
    )
    # If there are no parent groups, then just return whatever the current integration
    # status is. It should be either `NOT_STARTED` or `QUEUED`.
    integration_db_obj = db.get_object(
        db_type=Integration, where_conditions={"id": integration_id}
    )
    if not parent_groups:
        return UpdatedIntegrationParentGroups(
            integration=integration_db_obj, parent_groups={}
        )

    # Otherwise, update each parent group's status based on the status of their jobs.
    updated_parent_groups: dict[str, ParentGroupData] = {
        pg.parent_group_id: update_parent_group_status(
            pg.parent_group_id, namespace=namespace, db=db
        )
        for pg in parent_groups
    }
    pg_statuses = [pg.status for _, pg in updated_parent_groups.items()]
    if any([status == IntegrationStatus.FAILED for status in pg_statuses]):
        integration_status = IntegrationStatus.FAILED
    elif any([status == IntegrationStatus.RUNNING for status in pg_statuses]):
        integration_status = IntegrationStatus.RUNNING
    elif all([status == IntegrationStatus.SUCCESS for status in pg_statuses]):
        integration_status = IntegrationStatus.SUCCESS
    elif any([status == IntegrationStatus.QUEUED for status in pg_statuses]):
        integration_status = IntegrationStatus.QUEUED
    # Otherwise, don't change the integration status just yet...
    else:
        integration_status = integration_db_obj.status

    updated_integration_obj = db.update_object(
        db_type=Integration,
        where_conditions={
            "id": integration_id,
        },
        status=integration_status,
    )
    return UpdatedIntegrationParentGroups(
        integration=updated_integration_obj, parent_groups=updated_parent_groups
    )


def get_non_null_attributes_from_data(
    data: T, exclude: list[str] | None = None
) -> dict[str, Any]:
    non_null_attributes = {}
    for field, _ in data.model_fields.items():
        if exclude and field in exclude:
            continue
        attr_value = getattr(data, field)
        if attr_value is not None:
            non_null_attributes[field] = attr_value
    return non_null_attributes
