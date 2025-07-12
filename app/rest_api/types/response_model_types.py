from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models.choices import ChatModelProvider
from app.db.models.integration import Integration, ParentGroupData


class Token(BaseModel):
    access_token: str
    token_type: str


class UpdatedIntegrationParentGroups(BaseModel):
    integration: Integration
    parent_groups: dict[str, ParentGroupData]


class ChatModelResponseModel(BaseModel):
    id: UUID
    created_at: datetime
    provider: ChatModelProvider
    model_name: str
    user_id: UUID
    secret_id: UUID
    secret_slug: str
