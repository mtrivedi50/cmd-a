from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.db.models.choices import (
    ChatModelProvider,
    IntegrationType,
    SecretType,
)


class NewUserDataInput(BaseModel):
    """For creating a new user via the sign-up flow"""

    username: str
    password: str
    first_name: str
    last_name: str
    is_admin: bool = False
    is_staff: bool = False


class ExistingUserDataInput(BaseModel):
    """For updating an existing user via a PATCH request"""

    username: str | None = None
    password: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
    is_staff: bool | None = None


class SecretInput(BaseModel):
    name: str
    type: SecretType = SecretType.API_KEY
    data: dict[str, Any]


class ExistingSecretInput(BaseModel):
    name: str | None = None
    type: SecretType | None = None
    data: dict[str, Any] | None = None


class IntegrationInput(BaseModel):
    name: str
    type: IntegrationType
    secret_id: UUID
    schedule: Literal["@hourly", "@daily", "@weekly"] | str
    is_active: bool = True


class ExistingIntegrationInput(BaseModel):
    """
    Used for updating integration objects via a PATCH request.
    """

    name: str | None = None
    type: IntegrationType | None = None
    secret_id: UUID | None = None
    schedule: Literal["@hourly", "@daily", "@weekly"] | str | None = None
    is_active: bool | None = None


class ChatModelInput(BaseModel):
    provider: ChatModelProvider
    model_name: str
    secret_id: str


class ExistingChatModelInput(BaseModel):
    """
    Used for updating chat model objects via a PATCH request.
    """

    provider: ChatModelProvider | None = None
    model_name: str | None = None
    secret_id: str | None = None


class NewConversationInput(BaseModel):
    chat_id: UUID
    query: str


class ChatCompletionInput(BaseModel):
    chat_id: UUID
    chat_model_name: str
    chat_model_secret_slug: str
    chat_model_provider: ChatModelProvider
    query: str
    integration_ids: list[UUID]
