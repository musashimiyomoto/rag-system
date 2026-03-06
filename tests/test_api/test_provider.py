import pytest
from pytest_httpx import HTTPXMock

from constants.github import GITHUB_MODELS_URL
from enums import ProviderName
from tests.base import BaseTestCase
from tests.factories import ProviderFactory


class TestCreateProvider(BaseTestCase):
    url = "/provider"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        response = await self.client.post(
            url=self.url,
            json={"name": ProviderName.GITHUB.value, "api_key": "test-api-key"},
        )

        data = await self.assert_response_ok(response=response)
        assert data["id"] is not None
        assert data["name"] == ProviderName.GITHUB.value
        assert data["is_active"] is True


class TestGetProviders(BaseTestCase):
    url = "/provider/list"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        provider_count = 2
        [
            await ProviderFactory.create_async(session=self.session)
            for _ in range(provider_count)
        ]

        response = await self.client.get(url=self.url)

        data = await self.assert_response_ok(response=response)
        assert isinstance(data, list)
        assert len(data) == provider_count


class TestUpdateProvider(BaseTestCase):
    url = "/provider/{provider_id}"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        provider = await ProviderFactory.create_async(session=self.session)

        response = await self.client.patch(
            url=self.url.format(provider_id=provider.id),
            json={"is_active": False},
        )

        data = await self.assert_response_ok(response=response)
        assert data["id"] == provider.id
        assert data["is_active"] is False


class TestDeleteProvider(BaseTestCase):
    url = "/provider/{provider_id}"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        provider = await ProviderFactory.create_async(session=self.session)

        response = await self.client.delete(
            url=self.url.format(provider_id=provider.id)
        )

        await self.assert_response_ok(response=response)


class TestGetProviderModels(BaseTestCase):
    url = "/provider/{provider_id}/models"

    @pytest.mark.asyncio
    async def test_ok(self, httpx_mock: HTTPXMock) -> None:
        expected_model_count = 2
        create_response = await self.client.post(
            url="/provider",
            json={"name": ProviderName.GITHUB.value, "api_key": "test-api-key"},
        )
        provider_data = await self.assert_response_ok(response=create_response)
        httpx_mock.add_response(
            method="GET",
            url=GITHUB_MODELS_URL,
            json=[{"id": "gpt-4.1"}, {"id": "o3-mini"}],
        )

        response = await self.client.get(
            url=self.url.format(provider_id=provider_data["id"])
        )

        data = await self.assert_response_ok(response=response)
        assert isinstance(data, list)
        assert len(data) == expected_model_count
        assert data[0]["name"] == "gpt-4.1"
