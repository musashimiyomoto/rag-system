import pytest

from tests.base import BaseTestCase


class TestHealthLiveness(BaseTestCase):
    url = "/health/liveness"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        response = await self.client.get(url=self.url)

        data = await self.assert_response_ok(response=response)
        assert data["status"] is True


class TestHealthReadiness(BaseTestCase):
    url = "/health/readiness"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        response = await self.client.get(url=self.url)

        data = await self.assert_response_ok(response=response)
        assert "services" in data
        assert "status" in data
        assert isinstance(data["services"], list)
        assert isinstance(data["status"], bool)
        assert any(service["name"] == "qdrant" for service in data["services"])
