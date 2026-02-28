from sqlalchemy.ext.asyncio import AsyncSession

from ai.providers import list_provider_models
from db.repositories import ProviderRepository
from exceptions import ProviderConflictError, ProviderNotFoundError
from schemas import (
    ProviderCreateRequest,
    ProviderModelResponse,
    ProviderResponse,
    ProviderUpdateRequest,
)
from utils import decrypt, encrypt


class ProviderUsecase:
    def __init__(self):
        self._provider_repository = ProviderRepository()

    async def create_provider(
        self,
        session: AsyncSession,
        data: ProviderCreateRequest,
    ) -> ProviderResponse:
        """Create provider.

        Args:
            session: The session parameter.
            data: The data parameter.

        Returns:
            The created provider response.

        """
        return ProviderResponse.model_validate(
            await self._provider_repository.create(
                session=session,
                data={
                    "name": data.name,
                    "api_key_encrypted": encrypt(data=data.api_key),
                    "is_active": True,
                },
            )
        )

    async def get_providers(self, session: AsyncSession) -> list[ProviderResponse]:
        """Get providers.

        Args:
            session: The session parameter.

        Returns:
            The list of configured providers.

        """
        return [
            ProviderResponse.model_validate(provider)
            for provider in await self._provider_repository.get_all(session=session)
        ]

    async def update_provider(
        self, session: AsyncSession, provider_id: int, data: ProviderUpdateRequest
    ) -> ProviderResponse:
        """Update provider.

        Args:
            session: The session parameter.
            provider_id: The provider_id parameter.
            data: The data parameter.

        Returns:
            The updated provider response.

        """
        updated_data = data.model_dump(exclude_none=True)
        if not updated_data:
            raise ProviderConflictError(message="No data provided for update")

        provider = await self._provider_repository.get_by(
            session=session, id=provider_id
        )
        if not provider:
            raise ProviderNotFoundError

        return ProviderResponse.model_validate(
            await self._provider_repository.update_by(
                session=session, id=provider_id, data=updated_data
            )
        )

    async def delete_provider(self, session: AsyncSession, provider_id: int) -> None:
        """Delete provider.

        Args:
            session: The session parameter.
            provider_id: The provider_id parameter.

        """
        deleted = await self._provider_repository.delete_by(
            session=session, id=provider_id
        )
        if not deleted:
            raise ProviderNotFoundError

    async def get_provider_models(
        self, session: AsyncSession, provider_id: int
    ) -> list[ProviderModelResponse]:
        """Get provider models.

        Args:
            session: The session parameter.
            provider_id: The provider_id parameter.

        Returns:
            The list of available models for the provider.

        """
        provider = await self._provider_repository.get_by(
            session=session, id=provider_id
        )
        if not provider:
            raise ProviderNotFoundError
        if not provider.is_active:
            raise ProviderConflictError(message="Provider is inactive")

        return list_provider_models(
            name=provider.name,
            api_key=decrypt(encrypted_data=provider.api_key_encrypted),
        )
