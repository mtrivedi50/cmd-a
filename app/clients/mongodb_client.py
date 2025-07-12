import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from pymongo import MongoClient
from pymongo.server_api import ServerApi

from app.db.models.choices import ChatRole

# Logger
logger = logging.getLogger(__name__)


class Citation(BaseModel):
    citation_number: int
    citation: dict[str, Any]


class Message(BaseModel):
    user_id: UUID | str
    chat_id: UUID | str
    role: ChatRole
    content: str
    context: str = Field(default="")
    ts: str
    citations: list[Citation] = Field(default_factory=list)

    @model_validator(mode="after")
    def convert_uuids_to_strings(self) -> "Message":
        self.user_id = str(self.user_id)
        self.chat_id = str(self.chat_id)
        return self


class Chat(BaseModel):
    user_id: UUID | str
    namespace: str = Field(default="default")
    chat_id: UUID | str
    title: str
    query: str
    ts: str

    @model_validator(mode="after")
    def convert_uuids_to_strings(self) -> "Chat":
        self.user_id = str(self.user_id)
        self.chat_id = str(self.chat_id)
        return self


class DocumentStoreClient:
    client: MongoClient

    def __init__(
        self,
        mongodb_driver: str,
        mongodb_user: str,
        mongodb_password: str,
        mongodb_host: str,
        mongodb_port: str | None,
        mongodb_options: str | None = None,
    ):
        full_host = mongodb_host
        if mongodb_port is not None:
            full_host += f":{mongodb_port}"

        connection_uri_template = "{driver}://{mongodb_user}:{mongodb_password}@{mongodb_host}{mongodb_port}/{mongodb_options}"
        connection_uri = connection_uri_template.format(
            driver=mongodb_driver,
            mongodb_user=mongodb_user,
            mongodb_password=mongodb_password,
            mongodb_host=mongodb_host,
            mongodb_port=mongodb_port if mongodb_port is not None else "",
            mongodb_options=(
                ("?" + urlencode(json.loads(mongodb_options)))
                if mongodb_options is not None
                else ""
            ),
        )
        self.client = MongoClient(
            connection_uri, server_api=ServerApi(version="1", strict=True)
        )

        # Database
        self.db = self.client["cmd-a"]
        self.chats_collection = self.db["chats"]
        self.context_collection = self.db["context"]
        self.messages_collection = self.db["messages"]

    def delete_chat(
        self,
        user_id: UUID,
        chat_id: UUID,
    ):
        # Delete chat
        self.chats_collection.delete_one(
            filter={
                "user_id": str(user_id),
                "chat_id": str(chat_id),
            }
        )

        # Delete all messages in the chat
        self.messages_collection.delete_many(
            filter={
                "user_id": str(user_id),
                "chat_id": str(chat_id),
            }
        )

    def get_messages_from_chat(
        self,
        user_id: UUID,
        chat_id: UUID,
    ) -> list[dict[str, Any]]:
        cursor = self.messages_collection.find(
            {"user_id": str(user_id), "chat_id": str(chat_id)}
        ).sort({"ts": 1})
        return [mes for mes in cursor]

    def add_messages_to_chat(self, messages: list[dict[str, Any]]):
        # For validation...we only insert a couple messages at a time, so this shouldn't
        # take too long (hopefully).
        self.messages_collection.insert_many(messages)

    def add_chat(self, chat: Chat):
        self.chats_collection.insert_one(chat.model_dump())

    def add_context(self, context: dict[str, str]):
        self.context_collection.insert_one(context)

    def get_chat(self, chat_id: UUID) -> Chat:
        chats = self.chats_collection.find({"chat_id": str(chat_id)})
        chat_objects = [Chat(**chat_dict) for chat_dict in chats]
        if not chat_objects:
            raise Exception(f"Chat with ID {chat_id} not found!")
        return chat_objects[0]

    def get_chats_for_user(
        self, user_id: UUID, days: int | None
    ) -> list[dict[str, str]]:
        query: dict[str, Any] = {
            "user_id": str(user_id),
        }
        if days is not None:
            ts_lower_bound = str(
                (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
            )
            query["ts"] = {"$gte": ts_lower_bound}
        cursor = self.chats_collection.find(query).sort({"ts": -1})
        return [convo for convo in cursor]

    @staticmethod
    def add_context_to_message(message: str, context: str) -> str:
        return message + "\n" + context if context else message
