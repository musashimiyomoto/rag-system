from prefect import task

from ai.providers import list_provider_models
from ai.summarize import summarize
from db.repositories import ProviderRepository, SourceRepository
from db.sessions import async_session
from enums import SourceStatus
from utils import decrypt


@task(name="Summarize Source")
async def _summarize_source(source_id: int, chunks: list[str]) -> str:
    """Summarize source chunks using active provider."""
    source_repository = SourceRepository()

    async with async_session() as session:
        provider = await ProviderRepository().get_by(session=session, is_active=True)
        if not provider or not provider.is_active:
            await source_repository.update_by(
                session=session, id=source_id, data={"status": SourceStatus.FAILED}
            )
            msg = "No active provider found!"
            raise ValueError(msg)

    models = list_provider_models(
        name=provider.name,
        api_key=decrypt(encrypted_data=provider.api_key_encrypted),
    )
    if len(models) == 0:
        async with async_session() as session:
            await source_repository.update_by(
                session=session, id=source_id, data={"status": SourceStatus.FAILED}
            )
        msg = f"No models found for provider {provider.name}!"
        raise ValueError(msg)

    return await summarize(
        texts=chunks,
        provider_name=provider.name,
        model_name=models[0].name,
        api_key_encrypted=provider.api_key_encrypted,
    )
