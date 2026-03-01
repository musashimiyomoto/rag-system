from http import HTTPStatus

import pytest

from enums import ProviderName
from tests.base import BaseTestCase
from tests.factories import ProviderFactory
from utils import decrypt


class TestProvider(BaseTestCase):
    url = "/provider"

    @pytest.mark.asyncio
    async def test_create_ollama_without_api_key_ok(self) -> None:
        response = await self.client.post(url=self.url, json={"name": "ollama"})
        data = await self.assert_response_ok(response=response)
        assert data["name"] == "ollama"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_openai_without_api_key_returns_422(self) -> None:
        response = await self.client.post(url=self.url, json={"name": "openai"})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_google_without_api_key_returns_422(self) -> None:
        response = await self.client.post(url=self.url, json={"name": "google"})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_provider_encrypts_api_key(self) -> None:
        provider = await ProviderFactory.create_async(
            session=self.session,
            name=ProviderName.OPENAI,
            api_key_encrypted="old-encrypted",
        )
        response = await self.client.patch(
            url=f"{self.url}/{provider.id}",
            json={"api_key": "new-key"},
        )
        data = await self.assert_response_ok(response=response)
        assert decrypt(data["api_key_encrypted"]) == "new-key"
