import asyncio
from collections.abc import Generator
from dataclasses import dataclass
from typing import AsyncGenerator, TypedDict
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.ollama import OllamaContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.qdrant import QdrantContainer
from testcontainers.redis import RedisContainer

import db.sessions as db_sessions
from ai.dependencies import AgentDeps
from ai.vector_store import _get_client
from api.dependencies import agent, db
from db.models import Base
from main import app
from settings import (
    core_settings,
    ollama_settings,
    postgres_settings,
    qdrant_settings,
    redis_settings,
)


class PostgresCredentials(TypedDict):
    host: str
    port: int
    database: str
    user: str
    password: str


@dataclass(frozen=True)
class RuntimeState:
    qdrant_host: str
    qdrant_port: int
    redis_host: str
    redis_port: int
    redis_db: int
    disable_source_flow_deploy: bool
    async_engine: AsyncEngine
    async_session_factory: async_sessionmaker[AsyncSession]


def _build_postgres_credentials(connection_url: str) -> PostgresCredentials:
    parsed_url = make_url(connection_url)

    if (
        parsed_url.host is None
        or parsed_url.port is None
        or parsed_url.database is None
        or parsed_url.username is None
        or parsed_url.password is None
    ):
        msg = "Postgres connection URL is missing required components"
        raise RuntimeError(msg)

    return {
        "host": parsed_url.host,
        "port": parsed_url.port,
        "database": parsed_url.database,
        "user": parsed_url.username,
        "password": parsed_url.password,
    }


def _snapshot_runtime_state() -> RuntimeState:
    return RuntimeState(
        qdrant_host=qdrant_settings.host,
        qdrant_port=qdrant_settings.port,
        redis_host=redis_settings.host,
        redis_port=redis_settings.port,
        redis_db=redis_settings.db,
        disable_source_flow_deploy=core_settings.disable_source_flow_deploy,
        async_engine=db_sessions.async_engine,
        async_session_factory=db_sessions.async_session,
    )


def _apply_runtime_overrides(
    postgres_url: str,
    qdrant_container: QdrantContainer,
    redis_container: RedisContainer,
) -> None:
    qdrant_settings.host = qdrant_container.get_container_host_ip()
    qdrant_settings.port = int(qdrant_container.get_exposed_port(6333))

    redis_settings.host = redis_container.get_container_host_ip()
    redis_settings.port = int(redis_container.get_exposed_port(redis_container.port))
    redis_settings.db = 0

    core_settings.disable_source_flow_deploy = True

    db_sessions.async_engine = create_async_engine(
        url=postgres_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_timeout=30,
        pool_recycle=1800,
    )
    db_sessions.async_session = async_sessionmaker(
        bind=db_sessions.async_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    _get_client.cache_clear()


def _restore_runtime_state(snapshot: RuntimeState) -> AsyncEngine:
    _get_client.cache_clear()

    qdrant_settings.host = snapshot.qdrant_host
    qdrant_settings.port = snapshot.qdrant_port
    redis_settings.host = snapshot.redis_host
    redis_settings.port = snapshot.redis_port
    redis_settings.db = snapshot.redis_db
    core_settings.disable_source_flow_deploy = snapshot.disable_source_flow_deploy

    test_engine = db_sessions.async_engine
    db_sessions.async_engine = snapshot.async_engine
    db_sessions.async_session = snapshot.async_session_factory

    return test_engine


def _dispose_engine_sync(engine: AsyncEngine | None) -> None:
    """Dispose async engine from sync fixture teardown via dedicated loop."""
    if engine is None:
        return

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(engine.dispose())
    finally:
        loop.close()


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer(image=postgres_settings.image, driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def qdrant_container() -> Generator[QdrantContainer, None, None]:
    with QdrantContainer(image=qdrant_settings.image) as qdrant:
        yield qdrant


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    with RedisContainer(image=redis_settings.image) as redis:
        yield redis


@pytest.fixture(scope="session")
def ollama_container() -> Generator[OllamaContainer, None, None]:
    original_host = ollama_settings.host
    original_port = ollama_settings.port

    with OllamaContainer(image=ollama_settings.image) as ollama:
        endpoint = urlparse(ollama.get_endpoint())
        if endpoint.hostname is None or endpoint.port is None:
            msg = "Ollama endpoint is missing host or port"
            raise RuntimeError(msg)

        ollama_settings.host = endpoint.hostname
        ollama_settings.port = endpoint.port
        yield ollama

    ollama_settings.host = original_host
    ollama_settings.port = original_port


@pytest.fixture(scope="session", autouse=True)
def test_runtime_settings(
    postgres_container: PostgresContainer,
    qdrant_container: QdrantContainer,
    redis_container: RedisContainer,
) -> Generator[None, None, None]:
    snapshot = _snapshot_runtime_state()

    _apply_runtime_overrides(
        postgres_url=postgres_container.get_connection_url(),
        qdrant_container=qdrant_container,
        redis_container=redis_container,
    )

    try:
        yield
    finally:
        _dispose_engine_sync(_restore_runtime_state(snapshot=snapshot))


@pytest.fixture(scope="session")
def postgres_credentials(
    postgres_container: PostgresContainer,
) -> PostgresCredentials:
    return _build_postgres_credentials(postgres_container.get_connection_url())


@pytest_asyncio.fixture(scope="function")
async def test_engine(
    postgres_container: PostgresContainer,
) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        url=postgres_container.get_connection_url(),
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session():
        yield test_session

    async def override_get_agent() -> Agent[AgentDeps, str]:
        return Agent(model=TestModel(), deps_type=AgentDeps, model_settings=None)

    app.dependency_overrides[db.get_session] = override_get_session
    app.dependency_overrides[agent.get_agent] = override_get_agent

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
