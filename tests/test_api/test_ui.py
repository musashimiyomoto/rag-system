from http import HTTPStatus

import pytest

from tests.base import BaseTestCase
from tests.factories import DocumentFactory


class TestMainPage(BaseTestCase):
    url = "/"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        response = await self.client.get(url=self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "text/html; charset=utf-8"

        content = await response.aread()
        assert len(content) > 0


class TestChatPage(BaseTestCase):
    url = "/chat/{document_id}"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        document = await DocumentFactory.create_async(session=self.session)

        response = await self.client.get(url=self.url.format(document_id=document.id))

        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        content = await response.aread()
        assert len(content) > 0
