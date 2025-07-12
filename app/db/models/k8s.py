from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import model_validator
from sqlmodel import Field, Relationship, UniqueConstraint

from app.db.models.base import CmdAModel
from app.db.models.choices import ExecutionRole, KubernetesResourceType, SecretType


class Secret(CmdAModel, table=True):  # type: ignore
    __tablename__ = "secrets"
    __table_args__ = (
        UniqueConstraint("name", "namespace", name="unique_name_namespace"),
    )

    type: SecretType
    name: str
    slug: str
    namespace: str
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    # `uselist` is for one-to-one relationships
    # https://docs.sqlalchemy.org/en/13/orm/basic_relationships.html#one-to-one
    integration: "Integration" = Relationship(  # type: ignore # noqa: F821
        back_populates="secret",
        cascade_delete=True,
        sa_relationship_kwargs={"uselist": False},
    )
    chat_model: "ChatModel" = Relationship(  # type: ignore # noqa: F821
        back_populates="secret",
        cascade_delete=True,
        sa_relationship_kwargs={"uselist": False},
    )


class K8sResource(CmdAModel, table=True):  # type: ignore
    __tablename__ = "k8s_resources"

    execution_role: ExecutionRole
    resource_type: KubernetesResourceType
    name: str

    # Integration can have many different Kubernetes resources (e.g., scheduler, worker)
    integration_id: UUID = Field(foreign_key="integrations.id", ondelete="CASCADE")
    integration: "Integration" = Relationship(  # type: ignore # noqa: F821
        back_populates="k8s_resources",
    )

    @model_validator(mode="before")
    @classmethod
    def compute_resource_name(cls, data: dict[str, Any]):
        data["name"] = f"{data['integration_type']}-{data['execution_role']}"
