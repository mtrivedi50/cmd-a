from uuid import UUID

from sqlmodel import Field, Relationship

from app.db.models.auth import User
from app.db.models.base import CmdAModel
from app.db.models.choices import ChatModelProvider
from app.db.models.k8s import Secret


class ChatModel(CmdAModel, table=True):  # type: ignore
    __tablename__ = "chat_models"

    provider: ChatModelProvider = Field(default=ChatModelProvider.OPENAI)
    model_name: str

    # Relationships
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="chat_models")
    secret_id: UUID = Field(foreign_key="secrets.id", ondelete="CASCADE")
    secret: Secret = Relationship(back_populates="chat_model")
