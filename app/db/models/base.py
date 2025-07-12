from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class CmdAModel(SQLModel):
    id: UUID = Field(primary_key=True, default_factory=uuid4, unique=True)
    created_at: datetime = Field(default_factory=datetime.now)
