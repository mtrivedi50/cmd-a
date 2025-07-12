from datetime import datetime
from uuid import UUID

from sqlmodel import Field, Relationship

from app.db.models.auth import User
from app.db.models.base import CmdAModel
from app.db.models.choices import (
    IntegrationStatus,
    IntegrationType,
    ParentGroupDataType,
)
from app.db.models.k8s import Secret


class ChunkProcessingJob(CmdAModel, table=True):  # type: ignore
    __tablename__ = "processing_jobs"

    name: str
    status: IntegrationStatus

    # Relationships
    parent_group_id: str = Field(
        foreign_key="parent_group_data.parent_group_id", ondelete="CASCADE"
    )
    parent_group_data: "ParentGroupData" = Relationship(
        back_populates="processing_jobs"
    )


class Integration(CmdAModel, table=True):  # type: ignore
    __tablename__ = "integrations"

    name: str
    type: IntegrationType
    last_run: datetime | None = Field(default=None)
    is_active: bool = Field(default=True)

    # Refresh schedule, represented as a cron
    refresh_schedule: str
    status: IntegrationStatus = Field(default=IntegrationStatus.NOT_STARTED)

    # Many-to-one relationships (many integrations, one parent)
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="integrations")
    secret_id: UUID = Field(foreign_key="secrets.id", ondelete="CASCADE")
    secret: Secret = Relationship(back_populates="integration")

    # One-to-many relationships (many children, one integration)
    k8s_resources: list["K8sResource"] = Relationship(  # type: ignore # noqa: F821
        back_populates="integration", cascade_delete=True
    )
    parent_group_data: list["ParentGroupData"] = Relationship(
        back_populates="integration", cascade_delete=True
    )


class ParentGroupData(CmdAModel, table=True):  # type: ignore
    __tablename__ = "parent_group_data"

    parent_group_id: str = Field(unique=True)
    name: str
    type: ParentGroupDataType
    record_count: int = Field(default=0)
    node_count: int = Field(default=0)
    edge_count: int = Field(default=0)
    status: IntegrationStatus = Field(default=IntegrationStatus.NOT_STARTED)
    last_run: datetime | None = Field(default=None)

    # Many-to-one
    integration_id: UUID = Field(foreign_key="integrations.id", ondelete="CASCADE")
    integration: Integration = Relationship(back_populates="parent_group_data")

    # One-to-many
    processing_jobs: list[ChunkProcessingJob] = Relationship(
        back_populates="parent_group_data", cascade_delete=True
    )
    vectors: list["UpsertedVector"] = Relationship(
        back_populates="parent_group_data", cascade_delete=True
    )


class UpsertedVector(CmdAModel, table=True):  # type: ignore
    __tablename__ = "vectors"

    vector_id: str = Field(unique=True)

    parent_group_id: str = Field(
        foreign_key="parent_group_data.parent_group_id", ondelete="CASCADE"
    )
    parent_group_data: ParentGroupData = Relationship(back_populates="vectors")
