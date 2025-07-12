from enum import StrEnum


class NodeLabel(StrEnum):
    PERSON = "Person"
    TEXT = "Text"
    FILE = "File"


class EdgeRelationship(StrEnum):
    # e.g., user created a message, PR, issue, etc.
    CREATED = "CREATED"
    # e.g., message has a file, reply,
    HAS = "HAS"
    # e.g., message is associated with a Notion page, GitHub PR, etc.
    LINKED_TO = "LINKED_TO"
