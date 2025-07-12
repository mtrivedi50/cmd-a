import logging
from typing import Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from kubernetes import config
from sqlmodel import select
from starlette.status import HTTP_202_ACCEPTED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from app.clients.k8s_client import KubernetesOperator
from app.db.container import Container
from app.db.factory import Database
from app.db.models.auth import User
from app.db.models.chat_models import ChatModel
from app.db.models.k8s import Secret
from app.db.security import get_current_user
from app.rest_api.types.input_types import (
    ChatModelInput,
    ExistingChatModelInput,
)
from app.rest_api.types.response_model_types import ChatModelResponseModel
from app.rest_api.utils import get_non_null_attributes_from_data

logger = logging.getLogger(__name__)


# Kubernetes client
config.incluster_config.load_incluster_config()


router = APIRouter()


@router.get(
    "/chat-model/{id}", tags=["ChatModel"], response_model=ChatModelResponseModel
)
@inject
async def get_chat_model(
    id: str,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> Any:
    stmt = (
        select(
            ChatModel.id,
            ChatModel.created_at,
            ChatModel.provider,
            ChatModel.model_name,
            ChatModel.user_id,
            Secret.id.label("secret_id"),  # type: ignore
            Secret.slug.label("secret_slug"),  # type: ignore
        )
        .join(Secret, Secret.id == ChatModel.secret_id)
        .where(ChatModel.user == user, ChatModel.id == UUID(id))
    )
    res = db.execute_stmt(stmt)
    if not res:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail=f"Chat model `{id}` not found!"
        )
    return res[0]


@router.get(
    "/chat-models", tags=["ChatModel"], response_model=list[ChatModelResponseModel]
)
@inject
async def list_chat_models(
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> list[Any]:
    stmt = (
        select(
            ChatModel.id,
            ChatModel.created_at,
            ChatModel.provider,
            ChatModel.model_name,
            ChatModel.user_id,
            Secret.id.label("secret_id"),  # type: ignore
            Secret.slug.label("secret_slug"),  # type: ignore
        )
        .join(Secret, Secret.id == ChatModel.secret_id)
        .where(ChatModel.user == user)
    )
    res = db.execute_stmt(stmt)
    return res


@router.post("/chat-model", tags=["ChatModel"])
@inject
async def create_chat_model(
    data: ChatModelInput,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> ChatModel:
    existing_chat_models = db.all_objects(
        db_type=ChatModel,
        where_conditions={
            "user": user,
            "provider": data.provider,
            "model_name": data.model_name,
        },
    )
    if existing_chat_models:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"`{data.model_name}` chat model for provider `{data.provider}` already exists!",
        )

    # Embedding model object
    chat_model_db_obj = ChatModel(
        provider=data.provider,
        model_name=data.model_name,
        user_id=user.id,
        secret_id=UUID(data.secret_id),
    )
    db.add(chat_model_db_obj)

    return chat_model_db_obj


@router.delete("/chat-model/{id}", tags=["ChatModel"])
@inject
async def delete_chat_model(
    id: str,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> dict[str, int | str]:
    with db.session() as session:
        chat_model_to_delete = db.get_object(
            db_type=ChatModel, where_conditions={"id": id}, session=session
        )
        # Confirm that we have the necessary permissions to delete
        if chat_model_to_delete.user_id != user.id:
            raise HTTPException(
                status_code=404,
                detail=f"Cannot delete chat model `{id}`, you are not the owner!",
            )

        # Destory the secret in Kubernetes and the database
        k8s_operator = KubernetesOperator()
        k8s_operator.destroy_secret(
            namespace=user.namespace, secret_name=chat_model_to_delete.secret.slug
        )
        db.delete(chat_model_to_delete.secret)

        # Delete chat model
        db.delete(chat_model_to_delete)

        return {
            "status_code": HTTP_202_ACCEPTED,
            "detail": f"Integration `{id}` successfully deleted!",
        }


@router.patch("/chat-model/{id}", tags=["ChatModel"])
@inject
async def patch_chat_model(
    id: str,
    data: ExistingChatModelInput,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> ChatModel:
    non_null_attributes = get_non_null_attributes_from_data(data)
    updated_chat_model = db.update_object(
        db_type=ChatModel,
        where_conditions={
            "id": id,
            "user_id": user.id,
        },
        **non_null_attributes,
    )
    return updated_chat_model
