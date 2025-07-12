import re
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_core import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


def use_fqdn(host: str) -> str:
    matches = re.match(r"^.*\.default\.svc\.cluster\.local.*$", host)

    # If there are no matches, then the host is just the service name. Use the FQDN.
    if matches is None:
        return f"{host}.default.svc.cluster.local"

    return host


class DeploymentMode(StrEnum):
    DEV: str = "dev"
    PROD: str = "prod"


class BaseDatabaseConfig(BaseModel, ABC):
    @abstractmethod
    def create_sqlalchemy_url(self) -> str:
        pass


class SqlLiteDatabaseConfig(BaseDatabaseConfig):
    engine: str
    name: str

    def create_sqlalchemy_url(self) -> str:
        return f"sqlite:///{self.name}.db"


class PostgresDatabaseConfig(BaseDatabaseConfig):
    engine: str = Field(default="postgresql+psycopg2")
    name: str
    user: str = Field(default="postgres")
    password: SecretStr
    host: str
    port: int = Field(default=5432)

    def create_sqlalchemy_url(self) -> str:
        return f"{self.engine}://{self.user}:{self.password.get_secret_value()}@{use_fqdn(self.host)}:{self.port}/{self.name}"


class RedisCredentials(BaseModel):
    HOST: str = Field(default="localhost")
    PASSWORD: str | None = Field(default=None)
    PORT: int = Field(default=6379)
    EXPIRATION: int = Field(default=60 * 60 * 24)

    @model_validator(mode="after")
    def define_host(self) -> "RedisCredentials":
        # Redis is always defined as a Kubernetes deployment/service
        self.HOST = use_fqdn(self.HOST)
        return self


class MongoDbOptions(BaseModel):
    retryWrites: bool
    w: str
    appName: str


class MongoDbCredentials(BaseModel):
    DRIVER: str = Field(default="mongodb")
    USER: str
    PASSWORD: str
    HOST: str
    PORT: str | None = Field(default=None)
    OPTIONS: str | None = Field(default=None)

    def define_host(self, mode: DeploymentMode):
        # In dev, we deploy MongoDb as a Kubernetes deployment/service
        if mode == DeploymentMode.DEV:
            self.HOST = use_fqdn(self.HOST)


class Neo4JCredentials(BaseModel):
    DRIVER: str = Field(default="neo4j")
    USER: str
    PASSWORD: str
    HOST: str

    def define_host(self, mode: DeploymentMode):
        # In dev, we deploy Neo4J as a Kubernetes deployment/service
        if mode == DeploymentMode.DEV:
            self.HOST = use_fqdn(self.HOST)

        # Add the driver, if necessary
        if f"{self.DRIVER}://" not in self.HOST:
            self.HOST = f"{self.DRIVER}://{self.HOST}"


class PineconeCredentials(BaseModel):
    API_KEY: str
    INDEX_MODEL: str = "llama-text-embed-v2"
    INDEX_HOST: str

    @model_validator(mode="after")
    def define_host(self) -> "PineconeCredentials":
        if "https://" not in self.INDEX_HOST:
            self.INDEX_HOST = f"https://{self.INDEX_HOST}"
        return self


class _Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")
    MODE: DeploymentMode
    ROOT: Path = Path(__file__).parent.parent
    APP_ROOT: Path = ROOT / "app"
    TEMPLATES_ROOT: Path = APP_ROOT / "rag" / "templates"

    # App name
    APP_NAME: str = Field(default="cmd-a")
    # Client origin - default URL for Vite React
    CLIENT_ORIGIN: str = Field(default="http://localhost:5173")
    # Redis Queue timeout
    QUEUE_TIMEOUT: int = 30
    # Objects to include in a single processing job
    MAX_OBJECTS_IN_JOB: int = 1000
    # Max number of processing jobs
    MAX_PROCESSING_JOBS: int = 2
    # Redis host
    REDIS: RedisCredentials
    # MongoDB credentials
    MONGO: MongoDbCredentials
    # Neo4J credentials
    NEO4J: Neo4JCredentials
    # Pinecone
    PINECONE: PineconeCredentials

    @model_validator(mode="after")
    def define_hosts(self) -> "_Settings":
        self.MONGO.define_host(mode=self.MODE)
        self.NEO4J.define_host(mode=self.MODE)
        return self


class _DevSettings(_Settings):
    DB: PostgresDatabaseConfig

    # Max number of processing jobs
    MAX_PROCESSING_JOBS: int = 2

    @model_validator(mode="after")
    def validate_mode(self) -> "_DevSettings":
        if self.MODE != DeploymentMode.DEV:
            raise ValidationError(
                f"Kubernetes development settings must be specified via `MODE=dev` environment variable! Found `MODE={self.mode}`."
            )
        return self

    def get_db_uri(self):
        return self.DB.create_sqlalchemy_url()


class _ProdSettings(_Settings):
    DB: PostgresDatabaseConfig

    # Max number of processing jobs
    MAX_PROCESSING_JOBS: int = 5

    @model_validator(mode="after")
    def validate_mode(self) -> "_ProdSettings":
        if self.MODE != DeploymentMode.PROD:
            raise ValidationError(
                f"Production settings must be specified via `MODE=prod` environment variable! Found `MODE={self.mode}`."
            )
        return self

    def get_db_uri(self):
        return self.DB.create_sqlalchemy_url()


deployment_mode = _Settings().MODE
if deployment_mode == DeploymentMode.DEV:
    Settings = _DevSettings()
else:
    Settings = _ProdSettings()
