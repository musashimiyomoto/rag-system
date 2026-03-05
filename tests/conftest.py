from collections.abc import Generator
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer
from testcontainers.qdrant import QdrantContainer

from ai.dependencies import AgentDeps
from api.dependencies import agent, db
from db.models import Base
from main import app
from settings import core_settings, postgres_settings, qdrant_settings


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer(image=postgres_settings.image, driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def qdrant_container() -> Generator[QdrantContainer, None, None]:
    with QdrantContainer(image=qdrant_settings.image) as qdrant:
        yield qdrant


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
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def test_qdrant(qdrant_container: QdrantContainer) -> None:
    qdrant_settings.host = qdrant_container.get_container_host_ip()
    qdrant_settings.port = qdrant_container.get_exposed_port(port=qdrant_settings.port)


@pytest_asyncio.fixture(scope="function")
async def test_client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    core_settings.disable_source_flow_deploy = True

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
