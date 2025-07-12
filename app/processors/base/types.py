import re
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from app.db.models.choices import ParentGroupDataType


class ProcessingParentGroupData(BaseModel):
    """Base class for parent data groups (e.g., Slack channel, GitHub repo)"""

    integration_id: str
    namespace: str
    type: ParentGroupDataType
    id: str
    oldest: str | None
    raw_api_response: dict[str, Any]

    _pretty_type: str = PrivateAttr()

    @model_validator(mode="after")
    def make_pretty(self) -> "ProcessingParentGroupData":
        split = self.type.split("_")
        self._pretty_type = " ".join([word.title() for word in split])
        return self


class ProcessingChunk(BaseModel):
    """Base class for data chunks to be processed"""

    parent_group_id: str
    parent_group_raw_api_response: dict[str, Any] = Field(default_factory=dict)
    id: str
    ts: str | None
    content: list[dict[str, Any]]

    @property
    def k8s_parent_group_id(self) -> str:
        # Create a job that name adheres to Kubernetes standards. Per the documentation:
        #   a lowercase RFC 1123 subdomain must consist of lower case alphanumeric
        #   characters, '-' or '.', and must start and end with an alphanumeric
        #   character (e.g. 'example.com')
        return re.sub(r"([^a-z0-9-.])", "-", self.parent_group_id.lower())
