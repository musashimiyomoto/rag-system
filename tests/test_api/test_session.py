import pytest

from enums import SourceStatus
from tests.base import BaseTestCase
from tests.factories import (
    MessageFactory,
    SessionFactory,
    SessionSourceFactory,
    SourceFactory,
)


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


class TestGetSessionMessages(BaseTestCase):
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
        session_count = 2
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
        assert len(data) == session_count
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
