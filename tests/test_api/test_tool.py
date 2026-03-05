import pytest

from tests.base import BaseTestCase


class TestToolList(BaseTestCase):
    url = "/tool/list"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        response = await self.client.get(url=self.url)

        data = await self.assert_response_ok(response=response)
        assert isinstance(data, list)
