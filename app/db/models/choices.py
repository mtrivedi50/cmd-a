from enum import StrEnum


class SecretType(StrEnum):
    API_KEY: str = "API Key"
    SLACK_WEB_TOKEN: str = "Slack Web Token"
    GITHUB_ACCESS_TOKEN: str = "GitHub Access Token"


class ChatModelProvider(StrEnum):
    # https://ai.pydantic.dev/models/
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"
    MISTRAL = "mistral"


class IntegrationType(StrEnum):
    SLACK: str = "slack"
    JIRA: str = "jira"
    NOTION: str = "notion"
    GITHUB: str = "github"


class ExecutionRole(StrEnum):
    # Generally, processors require two resources — a scheduler and a worker. The
    # scheduler is responsible for intermittently pinging the appropriate API and adds
    # data to the queue. It is deployed as a Kubernetes CRON job. The worker is
    # responsible for reading from the queue and actually processing the data (adding to
    # the graph database and the vector database).
    SCHEDULER: str = "scheduler"
    WORKER: str = "worker"


class KubernetesResourceType(StrEnum):
    DEPLOYMENT: str = "deployment"
    CRON_JOB: str = "cronjob"
    POD: str = "pod"
    SERVICE: str = "service"


class IntegrationStatus(StrEnum):
    NOT_STARTED: str = "not_started"
    QUEUED: str = "queued"
    RUNNING: str = "running"
    SUCCESS: str = "success"
    FAILED: str = "failed"


class ParentGroupDataType(StrEnum):
    SLACK_CHANNEL: str = "slack_channel"
    JIRA_EPIC: str = "jira_epic"
    NOTION_PAGE: str = "notion_page"
    GITHUB_REPO: str = "github_repository"


class ChatRole(StrEnum):
    USER: str = "user"
    ASSISTANT: str = "assistant"
