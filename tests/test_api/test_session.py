import pytest

from tests.base import BaseTestCase
from tests.factories import DocumentFactory, MessageFactory, SessionFactory


class TestCreateSession(BaseTestCase):
    url = "/session"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        document = await DocumentFactory.create_async(session=self.session)

        response = await self.client.post(
            url=self.url, json={"document_id": document.id}
        )

        data = await self.assert_response_ok(response=response)
        assert data["id"] is not None
        assert data["document_id"] == document.id
        assert data["created_at"] is not None


class TestGetMessages(BaseTestCase):
    url = "/session/{session_id}/message/list"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        message_count = 3
        document = await DocumentFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(
            session=self.session, document_id=document.id
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


class TestDeleteSession(BaseTestCase):
    url = "/session/{session_id}"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        document = await DocumentFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(
            session=self.session, document_id=document.id
        )

        response = await self.client.delete(url=self.url.format(session_id=session.id))

        await self.assert_response_ok(response=response)
