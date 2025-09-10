from http import HTTPStatus

import pytest_asyncio
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession


class BaseTestCase:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, test_session: AsyncSession, test_client: AsyncClient):
        self.session = test_session
        self.client = test_client

    async def assert_response_ok(self, response: Response) -> dict:
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.ACCEPTED]
        return response.json()

    async def assert_response_stream(self, response: Response) -> None:
        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        content = b""
        async for chunk in response.aiter_bytes():
            content += chunk
        assert isinstance(content, bytes)
        assert len(content) > 0
