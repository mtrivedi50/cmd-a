import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from redis import StrictRedis


class RedisClient(BaseModel):
    redis_host: str
    redis_port: int
    redis_db: int = Field(default=0)
    redis_password: str | None = Field(default=None)
    expiration: int

    _client: StrictRedis

    @model_validator(mode="after")
    def create_client(self) -> "RedisClient":
        kwargs = {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "decode_responses": True,
        }
        if self.redis_password:
            kwargs["password"] = self.redis_password
        self._client = StrictRedis(**kwargs)  # type: ignore
        return self

    def add_messages_to_redis(
        self, chat_id: str | UUID, messages: list[dict[str, Any]]
    ):
        self._client.rpush(str(chat_id), *[json.dumps(m) for m in messages])
        self._client.expire(str(chat_id), self.expiration)

    def retrieve_messages_from_redis(self, chat_id: str | UUID) -> list[dict[str, Any]]:
        messages = self._client.lrange(str(chat_id), 0, -1)
        return [json.loads(m) for m in messages]

    def simple_get(self, key: str) -> Any:
        return self._client.get(key)

    def simple_lpush(self, *args, **kwargs):
        return self._client.lpush(*args, **kwargs)

    def simple_set(self, *args, **kwargs):
        return self._client.set(*args, **kwargs)

    def simple_brpop(self, *args, **kwargs):
        return self._client.brpop(*args, **kwargs)
