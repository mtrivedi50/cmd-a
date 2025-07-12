from sqlmodel import Field, Relationship

from app.db.models.base import CmdAModel


class User(CmdAModel, table=True):  # type: ignore
    __tablename__ = "users"

    # The username should be an email
    username: str = Field(primary_key=True)
    hashed_password: str
    first_name: str
    last_name: str
    is_active: bool = True
    is_admin: bool = False
    is_staff: bool = False
    namespace: str

    # Relationships
    integrations: list["Integration"] = Relationship(  # type: ignore # noqa: F821
        back_populates="user",
        cascade_delete=True,
    )
    chat_models: list["ChatModel"] = Relationship(  # type: ignore # noqa: F821
        back_populates="user",
        cascade_delete=True,
    )
