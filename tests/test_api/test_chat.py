from http import HTTPStatus

import pytest

from tests.base import BaseTestCase
from tests.factories import SessionFactory, SessionSourceFactory, SourceFactory


class TestChatStream(BaseTestCase):
    url = "/chat/stream"

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
