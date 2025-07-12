from dependency_injector import containers, providers
from dependency_injector.providers import Singleton
from neo4j import AsyncDriver, AsyncGraphDatabase, Driver, GraphDatabase
from pinecone import Pinecone, PineconeAsyncio

from app.clients.graph_client import GraphClient
from app.clients.mongodb_client import DocumentStoreClient
from app.clients.redis_client import RedisClient
from app.clients.vectordb_client import VectorDb
from app.db.factory import Database
from app.settings import Settings


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.db.security",
            "app.rest_api.auth",
            "app.rest_api.chat",
            "app.rest_api.integrations",
            "app.rest_api.chat_models",
            "app.rest_api.k8s",
            "app.rest_api.utils",
        ]
    )
    database: Singleton[Database] = providers.Singleton(
        Database,
        db_url=Settings.get_db_uri(),
        pool_size=10,
    )
    # MongoDB client
    # For long-term conversation storage
    mongodb: Singleton[DocumentStoreClient] = providers.Singleton(
        DocumentStoreClient,
        mongodb_driver=Settings.MONGO.DRIVER,
        mongodb_user=Settings.MONGO.USER,
        mongodb_password=Settings.MONGO.PASSWORD,
        mongodb_host=Settings.MONGO.HOST,
        mongodb_port=Settings.MONGO.PORT,
        mongodb_options=Settings.MONGO.OPTIONS,
    )
    # Redis client
    # For short-term conversation storage and worker queues
    redis_client: Singleton[RedisClient] = providers.Singleton(
        RedisClient,
        redis_host=Settings.REDIS.HOST,
        redis_port=Settings.REDIS.PORT,
        redis_db=0,
        redis_password=Settings.REDIS.PASSWORD,
        expiration=Settings.REDIS.EXPIRATION,
    )
    # Pinecone client
    # Vector database used to compute embeddings and store vectorized data
    pinecone_client: Singleton[Pinecone] = providers.Singleton(
        Pinecone, api_key=Settings.PINECONE.API_KEY
    )
    pinecone_client_asyncio: Singleton[PineconeAsyncio] = providers.Singleton(
        PineconeAsyncio, api_key=Settings.PINECONE.API_KEY
    )
    vector_db: Singleton[VectorDb] = providers.Singleton(
        VectorDb,
        pc=pinecone_client,
        async_pc=pinecone_client_asyncio,
    )
    # Neo4J client
    # Graph database for linking entities together
    neo4j_driver: Singleton[Driver] = providers.Singleton(
        GraphDatabase.driver,
        uri=Settings.NEO4J.HOST,
        auth=(Settings.NEO4J.USER, Settings.NEO4J.PASSWORD),
    )
    async_neo4j_driver: Singleton[AsyncDriver] = providers.Singleton(
        AsyncGraphDatabase.driver,
        uri=Settings.NEO4J.HOST,
        auth=(Settings.NEO4J.USER, Settings.NEO4J.PASSWORD),
    )
    graph_client: Singleton[GraphClient] = providers.Singleton(
        GraphClient, neo4j_driver=neo4j_driver, async_neo4j_driver=async_neo4j_driver
    )
