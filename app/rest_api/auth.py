import logging
from typing import Annotated, Any

import slugify
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from kubernetes import config
from passlib.context import CryptContext
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from app.clients.k8s_client import KubernetesOperator
from app.db.container import Container
from app.db.factory import Database
from app.db.models import User
from app.db.security import create_access_token, get_current_user
from app.rest_api.types.input_types import ExistingUserDataInput, NewUserDataInput
from app.rest_api.types.response_model_types import Token
from app.rest_api.utils import get_non_null_attributes_from_data

# Kubernetes client
config.incluster_config.load_incluster_config()


# Logger
logger = logging.getLogger(__file__)


# API router
router = APIRouter()


# Password context (for hashing)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post(
    "/token",
    tags=["User"],
)
@inject
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Database = Depends(Provide[Container.database]),
) -> Token:
    try:
        user = db.get_object(
            db_type=User, where_conditions={"username": form_data.username}
        )
    except HTTPException:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail={
                "reason": "username",
                "message": "Incorrect username!",
            },
        )

    # Check if password matches
    if not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail={
                "reason": "password",
                "message": "Incorrect password!",
            },
        )

    # Create access token
    access_token = create_access_token({"username": form_data.username})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/signup", tags=["User"])
@inject
async def signup(
    data: NewUserDataInput, db: Database = Depends(Provide[Container.database])
):
    # If user already exists, raise an error
    users = db.all_objects(db_type=User, where_conditions={"username": data.username})
    if users:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail={
                "reason": "username",
                "message": f"User with username `{data.username}` already exists!",
            },
        )

    # Create namespace
    k8s_operator = KubernetesOperator()
    namespace = slugify.slugify(f"{data.first_name} {data.last_name} {data.username}")
    k8s_operator.create_namespace(namespace)

    # Create an "all access" role and bind this to the default service account.
    # TODO – provide better role-based permissions
    role = k8s_operator.create_all_access_rbac_role(namespace)
    k8s_operator.create_role_binding(
        namespace, "default", role_name=k8s_operator.get_name_from_metadata(role)
    )

    # Create user
    user = User(
        username=data.username,
        hashed_password=pwd_context.hash(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        is_admin=data.is_admin,
        is_staff=data.is_staff,
        namespace=namespace,
    )
    db.add(user)

    # Create access token for the user
    access_token = create_access_token({"username": data.username})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/users", tags=["User"], response_model=list[User])
@inject
async def list_users(
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> Any:
    return db.all_objects(db_type=User)


@router.get("/user/me", tags=["User"])
@inject
async def get_current_user_info(
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> User:
    return user


@router.patch("/users/{id}", tags=["User"])
@inject
async def partial_update_user(
    id: str,
    data: ExistingUserDataInput,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> Token | None:
    if not user.is_staff:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"Current user does not have the permissions to update user with ID `{id}`.",
        )
    non_null_attributes = get_non_null_attributes_from_data(data)

    # Replace password with hashed password
    if "password" in non_null_attributes:
        password = non_null_attributes.pop("password")
        hashed_password = pwd_context.hash(password)
        non_null_attributes["hashed_password"] = hashed_password

    db.update_object(
        db_type=User,
        where_conditions={
            "id": id,
        },
        **non_null_attributes,
    )

    # Return new token if needed
    if "username" in non_null_attributes:
        access_token = create_access_token(
            {"username": non_null_attributes["username"]}
        )
        return Token(access_token=access_token, token_type="bearer")

    return None


@router.delete("/users/{id}", tags=["User"])
@inject
async def delete_user(
    id: str,
    user: User = Depends(get_current_user),
    db: Database = Depends(Provide[Container.database]),
) -> dict[str, Any]:
    if not user.is_staff:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"Current user does not have the permissions to delete user with ID {id}.",
        )
    user_to_delete = db.get_object(db_type=User, where_conditions={"id": id})
    db.delete(user_to_delete)

    # Delete user namespace. Not recommended to use mixins class directly, but
    # whatever...
    k8s_operator = KubernetesOperator()
    k8s_operator.destroy_namespace(user_to_delete.namespace)
    return {"status_code": 202, "detail": f"User `{id}` successfully deleted!"}
