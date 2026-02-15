from http import HTTPStatus

import pytest

from enums import SourceStatus
from tests.base import BaseTestCase
from tests.factories import (
    MessageFactory,
    SessionFactory,
    SessionSourceFactory,
    SourceFactory,
)

SESSION_COUNT = 2


class TestCreateSession(BaseTestCase):
    url = "/session"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        source = await SourceFactory.create_async(
            session=self.session, status=SourceStatus.COMPLETED
        )

        response = await self.client.post(
            url=self.url, json={"source_ids": [source.id]}
        )

        data = await self.assert_response_ok(response=response)
        assert data["id"] is not None
        assert data["source_ids"] == [source.id]
        assert data["created_at"] is not None

    @pytest.mark.asyncio
    async def test_with_multiple_sources(self) -> None:
        source_1 = await SourceFactory.create_async(
            session=self.session, status=SourceStatus.COMPLETED
        )
        source_2 = await SourceFactory.create_async(
            session=self.session, status=SourceStatus.COMPLETED
        )

        response = await self.client.post(
            url=self.url,
            json={"source_ids": [source_1.id, source_2.id]},
        )

        data = await self.assert_response_ok(response=response)
        assert data["source_ids"] == [source_1.id, source_2.id]

    @pytest.mark.asyncio
    async def test_empty_source_ids(self) -> None:
        response = await self.client.post(url=self.url, json={"source_ids": []})
        data = await self.assert_response_ok(response=response)
        assert data["id"] is not None
        assert data["source_ids"] == []

    @pytest.mark.asyncio
    async def test_duplicate_source_ids_returns_400(self) -> None:
        source = await SourceFactory.create_async(
            session=self.session, status=SourceStatus.COMPLETED
        )
        response = await self.client.post(
            url=self.url, json={"source_ids": [source.id, source.id]}
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.asyncio
    async def test_missing_source_returns_404(self) -> None:
        response = await self.client.post(url=self.url, json={"source_ids": [99999]})
        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_not_completed_source_returns_409(self) -> None:
        source = await SourceFactory.create_async(
            session=self.session, status=SourceStatus.CREATED
        )
        response = await self.client.post(
            url=self.url, json={"source_ids": [source.id]}
        )
        assert response.status_code == HTTPStatus.CONFLICT


class TestGetMessages(BaseTestCase):
    url = "/session/{session_id}/message/list"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        message_count = 3
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )
        [
            await MessageFactory.create_async(
                session=self.session, session_id=session.id
            )
            for _ in range(message_count)
        ]

        response = await self.client.get(url=self.url.format(session_id=session.id))

        data = await self.assert_response_ok(response=response)
        assert len(data) == message_count


class TestGetSessions(BaseTestCase):
    url = "/session/list"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        old_session = await SessionFactory.create_async(session=self.session)
        new_session = await SessionFactory.create_async(session=self.session)
        source = await SourceFactory.create_async(
            session=self.session, status=SourceStatus.COMPLETED
        )
        await SessionSourceFactory.create_async(
            session=self.session, session_id=old_session.id, source_id=source.id
        )

        response = await self.client.get(url=self.url)

        data = await self.assert_response_ok(response=response)
        assert len(data) == SESSION_COUNT
        assert data[0]["id"] == new_session.id
        assert data[1]["id"] == old_session.id
        assert data[1]["source_ids"] == [source.id]


class TestUpdateSession(BaseTestCase):
    url = "/session/{session_id}"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        source_1 = await SourceFactory.create_async(
            session=self.session, status=SourceStatus.COMPLETED
        )
        source_2 = await SourceFactory.create_async(
            session=self.session, status=SourceStatus.COMPLETED
        )
        chat_session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=chat_session.id, source_id=source_1.id
        )
        await MessageFactory.create_async(
            session=self.session, session_id=chat_session.id
        )

        response = await self.client.patch(
            url=self.url.format(session_id=chat_session.id),
            json={"source_ids": [source_2.id]},
        )

        data = await self.assert_response_ok(response=response)
        assert data["source_ids"] == [source_2.id]

        messages_response = await self.client.get(
            url=f"/session/{chat_session.id}/message/list"
        )
        messages_data = await self.assert_response_ok(response=messages_response)
        assert len(messages_data) == 1

    @pytest.mark.asyncio
    async def test_missing_session_returns_404(self) -> None:
        response = await self.client.patch(
            url=self.url.format(session_id=99999),
            json={"source_ids": []},
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_duplicate_source_ids_returns_400(self) -> None:
        source = await SourceFactory.create_async(
            session=self.session, status=SourceStatus.COMPLETED
        )
        chat_session = await SessionFactory.create_async(session=self.session)

        response = await self.client.patch(
            url=self.url.format(session_id=chat_session.id),
            json={"source_ids": [source.id, source.id]},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.asyncio
    async def test_missing_source_returns_404(self) -> None:
        chat_session = await SessionFactory.create_async(session=self.session)
        response = await self.client.patch(
            url=self.url.format(session_id=chat_session.id),
            json={"source_ids": [99999]},
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_not_completed_source_returns_409(self) -> None:
        source = await SourceFactory.create_async(
            session=self.session, status=SourceStatus.CREATED
        )
        chat_session = await SessionFactory.create_async(session=self.session)
        response = await self.client.patch(
            url=self.url.format(session_id=chat_session.id),
            json={"source_ids": [source.id]},
        )
        assert response.status_code == HTTPStatus.CONFLICT


class TestDeleteSession(BaseTestCase):
    url = "/session/{session_id}"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=session.id, source_id=source.id
        )

        response = await self.client.delete(url=self.url.format(session_id=session.id))

        await self.assert_response_ok(response=response)
