from http import HTTPStatus

import pytest

from tests.base import BaseTestCase
from tests.factories import SessionFactory, SessionSourceFactory, SourceFactory


class TestChatStream(BaseTestCase):
    url = "/chat/stream"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )
        data = {"message": "Hello, how are you?", "session_id": session.id}
        params = {"provider_id": 1, "model_name": "test-model"}

        response = await self.client.post(url=self.url, json=data, params=params)
        await self.assert_response_stream(response=response)

    @pytest.mark.asyncio
    async def test_ok_with_web_search_tool(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )
        data = {"message": "Hello, how are you?", "session_id": session.id}
        params = {
            "provider_id": 1,
            "model_name": "test-model",
            "tool_ids": ["web_search"],
        }

        response = await self.client.post(url=self.url, json=data, params=params)
        await self.assert_response_stream(response=response)

    @pytest.mark.asyncio
    async def test_ok_with_web_search_tool_without_sources(self) -> None:
        session = await SessionFactory.create_async(session=self.session)
        data = {"message": "Hello, how are you?", "session_id": session.id}
        params = {
            "provider_id": 1,
            "model_name": "test-model",
            "tool_ids": ["web_search"],
        }

        response = await self.client.post(url=self.url, json=data, params=params)
        await self.assert_response_stream(response=response)

    @pytest.mark.asyncio
    async def test_unknown_tool_id_returns_409(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )
        data = {"message": "Hello, how are you?", "session_id": session.id}
        params = {
            "provider_id": 1,
            "model_name": "test-model",
            "tool_ids": ["unknown_tool"],
        }

        response = await self.client.post(url=self.url, json=data, params=params)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
