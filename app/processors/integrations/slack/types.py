from pydantic import BaseModel


class SlackSecret(BaseModel):
    token: str
