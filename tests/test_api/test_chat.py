import pytest

from enums import LLMName
from tests.base import BaseTestCase
from tests.factories import SessionFactory, SourceFactory


class TestChatStream(BaseTestCase):
    url = "/chat/stream"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        session = await SessionFactory.create_async(
            session=self.session, source_id=source.id
        )
        data = {"message": "Hello, how are you?", "session_id": session.id}

        response = await self.client.post(
            url=self.url, params={"llm": LLMName.OPENAI_GPT_5_NANO}, json=data
        )

        await self.assert_response_stream(response=response)
