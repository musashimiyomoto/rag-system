from typing import AsyncGenerator

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

from ai.dependencies import Dependencies
from api.dependencies import agent, db
from db.models import Base
from enums import LLMName
from main import app


@pytest_asyncio.fixture(scope="session")
async def postgres_container() -> AsyncGenerator[PostgresContainer, None]:
    with PostgresContainer() as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="function")
async def test_engine(
    postgres_container: PostgresContainer,
) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        url=postgres_container.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://", 1
        ),
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
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    def override_get_session():
        return test_session

    def override_get_agent(llm: LLMName) -> Agent[Dependencies, str]:
        return Agent(model=TestModel(), deps_type=Dependencies, model_settings=None)

    app.dependency_overrides[db.get_session] = override_get_session
    app.dependency_overrides[agent.get_agent] = override_get_agent

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
