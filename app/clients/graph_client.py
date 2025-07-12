import asyncio
import json
import re
from datetime import datetime
from typing import Any

from neo4j import AsyncDriver, Driver
from pydantic import BaseModel, model_validator

from app.db.models.choices import IntegrationType


def escape_neo4j_string(value: str | list[str]):
    """
    From Pinecone example:
    https://github.com/pinecone-io/pinecone-neo4j-explorer/blob/main/process_scotus.ipynb
    """
    if isinstance(value, str):
        return re.sub(r"(['\"\\])", r"\\\1", value)
    elif isinstance(value, list):
        return [re.sub(r"(['\"\\])", r"\\\1", v) for v in value]
    return value


class Node(BaseModel):
    integration_id: str
    id: str
    labels: list[str]
    source: IntegrationType

    @model_validator(mode="before")
    @classmethod
    def convert_id_to_string(cls, data: Any) -> Any:
        if "id" in data and isinstance(data["id"], int):
            data["id"] = str(data["id"])
        return data

    @model_validator(mode="after")
    def escape_neo4j_strings(self) -> "Node":
        self.id = escape_neo4j_string(self.id)
        self.labels = escape_neo4j_string(self.labels)
        return self

    @staticmethod
    def construct_label_string(labels: list[str], prefix: str = "n"):
        label_str = ":".join(labels)
        return f"{prefix}:{label_str}"

    def create_node_query(self) -> str:
        """
        See Neo4j docs:
        https://neo4j.com/docs/cypher-manual/current/clauses/merge/
        """
        prefix = "n"
        name_label_str = self.construct_label_string(labels=self.labels, prefix=prefix)

        # Model fields
        model_json = self.model_dump(exclude={"labels"})
        set_fields: list[str] = []
        for f, _ in model_json.items():
            set_fields.append(f"{prefix}.{f} = ${f}")
        set_str = ", ".join(set_fields)
        query = "\n ".join(
            [
                f"MERGE ({name_label_str} {{id: $id}})",
                f"ON CREATE SET {set_str}",
            ]
        )
        return query

    def create_node(self, driver: Driver):
        query = self.create_node_query()
        with driver.session() as session:
            session.run(query, **self.model_dump(exclude={"labels"}))


class TextNode(Node):
    content: str
    ts: str
    url: str | None
    display_name: str
    reactions: str

    @model_validator(mode="before")
    @classmethod
    def convert_reactions_list_to_str(cls, data: dict[str, Any]):
        if "reactions" in data and isinstance(data["reactions"], list):
            data["reactions"] = json.dumps(data["reactions"])
            return data
        else:
            data["reactions"] = "[]"
            return data

    @model_validator(mode="after")
    def process_text_node_attributes(self: "TextNode") -> "TextNode":
        self.content = escape_neo4j_string(self.content)
        self.ts = escape_neo4j_string(self.ts)
        if self.url:
            self.url = escape_neo4j_string(self.url)
        self.display_name = escape_neo4j_string(self.display_name)
        self.reactions = escape_neo4j_string(self.reactions)

        # Convert timestamp to UTC. We need to this on a source-by-source basis.
        if self.source == IntegrationType.SLACK:
            if self.ts:
                self.ts = datetime.fromtimestamp(float(self.ts)).isoformat()
        return self


class FileNode(Node):
    name: str
    mimetype: str
    url: str | None

    @model_validator(mode="after")
    def process_file_node_attributes(self: "FileNode") -> "FileNode":
        self.name = escape_neo4j_string(self.name)
        self.mimetype = escape_neo4j_string(self.mimetype)
        if self.url:
            self.url = escape_neo4j_string(self.url)
        return self


class PersonNode(Node):
    name_login: str

    @model_validator(mode="after")
    def process_person_node_attributes(self: "PersonNode") -> "PersonNode":
        self.name_login = escape_neo4j_string(self.name_login)
        return self


class Edge(BaseModel):
    from_node_id: str
    to_node_id: str
    relationship_type: str

    @model_validator(mode="before")
    @classmethod
    def convert_ids_to_string(cls, data: Any) -> Any:
        for key in ["from_node_id", "to_node_id"]:
            if key in data and isinstance(data[key], int):
                data[key] = str(data[key])
        return data

    @model_validator(mode="after")
    def escape_neo4j_strings(self) -> "Edge":
        self.from_node_id = escape_neo4j_string(self.from_node_id)
        self.to_node_id = escape_neo4j_string(self.to_node_id)
        self.relationship_type = escape_neo4j_string(self.relationship_type)
        return self

    def create_edge_query(self):
        return "\n ".join(
            [
                "MATCH (a {id: $fromNodeId}), (b {id: $toNodeId})",
                f"MERGE (a)-[r:{self.relationship_type}]->(b)",
            ]
        )

    def create_edge(self, driver: Driver):
        query = self.create_edge_query()
        with driver.session() as session:
            session.run(
                query,
                fromNodeId=self.from_node_id,
                toNodeId=self.to_node_id,
            )


class GraphClient:
    driver: Driver
    async_driver: AsyncDriver

    def __init__(self, neo4j_driver: Driver, async_neo4j_driver: AsyncDriver):
        self.driver = neo4j_driver
        self.async_driver = async_neo4j_driver
        self.edge_ids_map: dict[str, list[str]] = {}

    def add_node(self, node: Node):
        # If the node is a text node, but the content is empty,
        # then continue. This prevents empty nodes.
        if isinstance(node, TextNode):
            if node.content == "":
                return

        # If the file has a URL, check if there is a node whose ID matches that URL. If
        # it does, then update that node with the current node's attributes
        if hasattr(node, "url") and node.url is not None and node.url != "":
            set_safe_str = ",".join(
                [
                    f"n.{key} = ${key}"
                    for key, _ in node.model_dump(exclude={"labels"}).items()
                ]
            )
            cypher_query = (
                f"MATCH (n) WHERE n.id = $nodeUrl SET {set_safe_str} RETURN n"
            )
            res = self.execute_query(
                cypher_query, nodeUrl=node.url, **node.model_dump(exclude={"labels"})
            )
            if res:
                return
            else:
                node.create_node(self.driver)

        # Otherwise, create the node
        else:
            node.create_node(self.driver)

    def add_edge(self, edge: Edge):
        edge.create_edge(self.driver)

    def get_node_count(self, parent_group_id: str) -> int:
        parent_group_id_regex = f"(?i){parent_group_id}.*"
        query = "\n ".join(
            [
                "MATCH (n)",
                "WHERE n.id =~ $parentGroupIdRegex",
                "RETURN count(n) AS node_count;",
            ]
        )
        records, _, _ = self.driver.execute_query(
            query, parentGroupIdRegex=parent_group_id_regex
        )
        if not records:
            return 0
        else:
            return records[0]["node_count"]

    def get_edge_count(self, parent_group_id: str):
        parent_group_id_regex = f"(?i){parent_group_id}.*"
        query = "\n ".join(
            [
                "MATCH (a)-[r]->(b)",
                "WHERE a.id =~ $parentGroupIdRegex OR b.id =~ $parentGroupIdRegex",
                "RETURN count(r) AS relationship_count;",
            ]
        )
        records, _, _ = self.driver.execute_query(
            query, parentGroupIdRegex=parent_group_id_regex
        )
        if not records:
            return 0
        else:
            return records[0]["relationship_count"]

    def execute_query(self, cypher_query: str, **kwargs):
        with self.driver.session() as session:
            result = session.run(cypher_query, **kwargs)
            data = [record.data() for record in result]
        return data

    async def delete_integration(self, integration_id: str):
        cypher_query = """
        MATCH (n) WHERE n.integration_id = $integration_id
        DETACH DELETE n
        """
        async with self.async_driver.session() as session:
            await session.run(cypher_query, integration_id=str(integration_id))
        await asyncio.sleep(1)

    def get_nodes_from_url(self, url: str) -> list[Any]:
        cypher_query = """
        MATCH (n) WHERE n.url = $url
        RETURN n.id as id
        """
        return self.execute_query(cypher_query, url=url)
