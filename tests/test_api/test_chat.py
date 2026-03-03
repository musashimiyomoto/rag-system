import json
from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import pytest
from pydantic_ai import AgentRunResultEvent
from pydantic_ai.messages import (
    FunctionToolResultEvent,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolReturnPart,
    UserPromptPart,
)

from api.dependencies import agent
from main import app
from tests.base import BaseTestCase
from tests.factories import SessionFactory, SessionSourceFactory, SourceFactory

if TYPE_CHECKING:
    from pydantic_ai.run import AgentRunResult


class TestChatStream(BaseTestCase):
    url = "/chat/stream"

    @staticmethod
    async def _read_stream_chunks(response) -> list[dict]:
        payload = b""
        async for chunk in response.aiter_bytes():
            payload += chunk
        return [
            json.loads(line)
            for line in payload.decode("utf-8").splitlines()
            if line.strip()
        ]

    @pytest.mark.asyncio
    async def test_ok_without_tools(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )
        data = {
            "message": "Hello, how are you?",
            "session_id": session.id,
            "provider_id": 1,
            "model_name": "test-model",
            "tools": [],
        }

        response = await self.client.post(url=self.url, json=data)
        await self.assert_response_stream(response=response)

    @pytest.mark.asyncio
    async def test_ok_with_web_search_tool(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )
        data = {
            "message": "Hello, how are you?",
            "session_id": session.id,
            "provider_id": 1,
            "model_name": "test-model",
            "tools": [{"id": "web_search"}],
        }

        response = await self.client.post(url=self.url, json=data)
        await self.assert_response_stream(response=response)

    @pytest.mark.asyncio
    async def test_ok_with_retrieve_tool_and_session_sources(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )
        data = {
            "message": "Hello, how are you?",
            "session_id": session.id,
            "provider_id": 1,
            "model_name": "test-model",
            "tools": [{"id": "retrieve", "source_ids": [source.id]}],
        }

        response = await self.client.post(url=self.url, json=data)
        await self.assert_response_stream(response=response)

    @pytest.mark.asyncio
    async def test_stream_contains_web_search_result_chunk(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )

        class FakeRunResult:
            def new_messages(self) -> list:
                return [
                    ModelRequest(parts=[UserPromptPart(content="question")]),
                    ModelResponse(parts=[TextPart(content="answer")]),
                ]

        class FakeAgent:
            async def run_stream_events(self, **kwargs):
                _ = kwargs
                yield FunctionToolResultEvent(
                    result=ToolReturnPart(
                        tool_name="web_search", content="web result 1"
                    )
                )
                yield AgentRunResultEvent(
                    result=cast("AgentRunResult[str]", FakeRunResult())
                )

        async def override_get_agent():
            return FakeAgent()

        app.dependency_overrides[agent.get_agent] = override_get_agent

        response = await self.client.post(
            url=self.url,
            json={
                "message": "Hello, how are you?",
                "session_id": session.id,
                "provider_id": 1,
                "model_name": "test-model",
                "tools": [{"id": "web_search"}],
            },
        )

        assert response.status_code == HTTPStatus.OK
        chunks = await self._read_stream_chunks(response=response)
        assert any(chunk.get("web_search") == "web result 1" for chunk in chunks)

    @pytest.mark.asyncio
    async def test_stream_contains_retrieve_result_chunk(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )

        class FakeRunResult:
            def new_messages(self) -> list:
                return [
                    ModelRequest(parts=[UserPromptPart(content="question")]),
                    ModelResponse(parts=[TextPart(content="answer")]),
                ]

        class FakeAgent:
            async def run_stream_events(self, **kwargs):
                _ = kwargs
                yield FunctionToolResultEvent(
                    result=ToolReturnPart(tool_name="retrieve", content="retrieved row")
                )
                yield AgentRunResultEvent(
                    result=cast("AgentRunResult[str]", FakeRunResult())
                )

        async def override_get_agent():
            return FakeAgent()

        app.dependency_overrides[agent.get_agent] = override_get_agent

        response = await self.client.post(
            url=self.url,
            json={
                "message": "Hello, how are you?",
                "session_id": session.id,
                "provider_id": 1,
                "model_name": "test-model",
                "tools": [{"id": "retrieve", "source_ids": [source.id]}],
            },
        )

        assert response.status_code == HTTPStatus.OK
        chunks = await self._read_stream_chunks(response=response)
        assert any(chunk.get("retrieve") == "retrieved row" for chunk in chunks)

    @pytest.mark.asyncio
    async def test_ok_with_deep_think_tool(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )
        data = {
            "message": "Plan migration rollout",
            "session_id": session.id,
            "provider_id": 1,
            "model_name": "test-model",
            "tools": [{"id": "deep_think"}],
        }

        response = await self.client.post(url=self.url, json=data)
        await self.assert_response_stream(response=response)

    @pytest.mark.asyncio
    async def test_retrieve_without_source_ids_returns_422(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )
        data = {
            "message": "Hello, how are you?",
            "session_id": session.id,
            "provider_id": 1,
            "model_name": "test-model",
            "tools": [{"id": "retrieve"}],
        }

        response = await self.client.post(url=self.url, json=data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_unknown_tool_id_returns_422(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )
        data = {
            "message": "Hello, how are you?",
            "session_id": session.id,
            "provider_id": 1,
            "model_name": "test-model",
            "tools": [{"id": "unknown_tool"}],
        }

        response = await self.client.post(url=self.url, json=data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
