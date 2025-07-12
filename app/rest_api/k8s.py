import logging
from datetime import datetime
from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from kubernetes import config
from slugify import slugify
from starlette.status import HTTP_202_ACCEPTED

from app.clients.k8s_client import KubernetesOperator
from app.db.container import Container
from app.db.factory import Database
from app.db.models.auth import User
from app.db.models.k8s import Secret
from app.db.security import get_current_user
from app.rest_api.types.input_types import ExistingSecretInput, SecretInput
from app.rest_api.utils import get_non_null_attributes_from_data

logger = logging.getLogger(__name__)


# Kubernetes client
config.incluster_config.load_incluster_config()


router = APIRouter()


@router.get("/k8s-secret/{id}", tags=["K8s"], response_model=list[Secret])
@inject
async def get_secret(
    id: str,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> list[Any]:
    return db.get_object(
        db_type=Secret, where_conditions={"id": id, "namespace": user.namespace}
    )


@router.get("/k8s-secrets", tags=["K8s"], response_model=list[Secret])
@inject
async def list_secrets(
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> list[Any]:
    return db.all_objects(
        db_type=Secret, where_conditions={"namespace": user.namespace}
    )


@router.patch("/k8s-secret/{id}", tags=["K8s"])
@inject
async def update_secret(
    id: str,
    data: ExistingSecretInput,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> Secret:
    # Original secret
    original_secret = db.get_object(db_type=Secret, where_conditions={"id": id})
    non_null_attributes = get_non_null_attributes_from_data(data, exclude=["data"])
    non_null_attributes["updated_at"] = datetime.now()
    updated_secret = db.update_object(
        db_type=Secret, where_conditions={"id": id}, **non_null_attributes
    )

    operator = KubernetesOperator()

    # Secret data — if the user is not overwriting the secret data, then grab the
    # existing data.
    secret_data = (
        data.data
        if data.data is not None and data.data
        else operator.read_namespaced_secret(
            namespace=user.namespace, secret_name=original_secret.slug
        )
    )
    secret_name = slugify(data.name) if data.name is not None else original_secret.slug

    # If the name has changed, then delete the existing secret
    if "name" in non_null_attributes:
        operator.destroy_secret(namespace=user.namespace, secret_name=secret_name)

    # Update the secret in Kubernetes
    operator.create_or_update_secret(
        namespace=user.namespace,
        secret_name=secret_name,
        secret_data=secret_data,
    )

    # Return updated secret obj
    return updated_secret


@router.post("/k8s-secret", tags=["K8s"])
@inject
async def create_secret(
    data: SecretInput,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> Secret:
    secret_slug = slugify(data.name)
    operator = KubernetesOperator()
    operator.create_or_update_secret(
        namespace=user.namespace,
        secret_name=secret_slug,
        secret_data=data.data,
    )

    # Create database object
    secret_db_object = Secret(
        type=data.type,
        name=data.name,
        slug=secret_slug,
        namespace=user.namespace,
    )
    db.add(secret_db_object)
    return secret_db_object


@router.delete("/k8s-secret/{id}", tags=["K8s"])
@inject
async def delete_secret(
    id: str,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> dict[str, int | str]:
    secret_to_delete = db.get_object(
        db_type=Secret,
        where_conditions={"id": id},
    )

    # Delete Kubernetes secret and database object
    operator = KubernetesOperator()
    operator.destroy_secret(namespace=user.namespace, secret_name=secret_to_delete.slug)

    db.delete(secret_to_delete)

    return {
        "status_code": HTTP_202_ACCEPTED,
        "detail": f"Secret `{id}` successfully deleted!",
    }
