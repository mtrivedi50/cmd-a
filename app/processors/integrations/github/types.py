from enum import StrEnum

from pydantic import BaseModel, PrivateAttr, model_validator

from app.processors.base.types import ProcessingChunk


class GithubSecret(BaseModel):
    token: str
    org_name: str | None = None
    user_name: str | None = None

    _owner: str = PrivateAttr()

    @model_validator(mode="after")
    def validate_org_user_name(self) -> "GithubSecret":
        if self.org_name:
            self._owner = self.org_name
        elif self.user_name:
            self._owner = self.user_name
        else:
            raise Exception("Provide either `org_name` or `user_name`!")
        return self


class ContentType(StrEnum):
    PR: str = "pr"
    ISSUE: str = "issue"


class GithubProcessingChunk(ProcessingChunk):
    content_type: ContentType
