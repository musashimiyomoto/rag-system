from prefect import flow, task

from ai.providers import list_provider_models
from ai.summarize import summarize
from ai.vector_store import ensure_collection, upsert_chunks
from db.repositories import (
    ProviderRepository,
    SourceDbRepository,
    SourceFileRepository,
    SourceRepository,
)
from db.sessions import async_session
from enums import SourceStatus, SourceType
from flows.process_source.indexing import index_db_source, index_file_source
from settings import core_settings
from utils import decrypt


@task(name="Load Source Data")
async def _load_source_data(source_id: int) -> tuple[dict, bytes | None]:
    """Load source context and branch-specific payload for processing.

    Args:
        source_id: The ID of the source to load.

    Returns:
        A tuple containing the source data dictionary and the file content.

    Raises:
        ValueError: If the source is not found or if the source type is unsupported.

    """
    source_repository = SourceRepository()
    file_content: bytes | None = None

    async with async_session() as session:
        source = await source_repository.update_by(
            session=session,
            id=source_id,
            data={"status": SourceStatus.PROCESSED},
        )
        if not source:
            msg = f"Source №{source_id} not found!"
            raise ValueError(msg)

        if source.type in SourceType.get_db_types():
            source_db = await SourceDbRepository().get_by(
                session=session, source_id=source_id
            )
            if source_db is None:
                await source_repository.update_by(
                    session=session,
                    id=source_id,
                    data={"status": SourceStatus.FAILED},
                )
                msg = f"For source №{source_id} not found source_db!"
                raise ValueError(msg)
        else:
            source_file = await SourceFileRepository().get_by(
                session=session, source_id=source_id
            )
            if source_file is None:
                await source_repository.update_by(
                    session=session,
                    id=source_id,
                    data={"status": SourceStatus.FAILED},
                )
                msg = f"For source №{source_id} not found file!"
                raise ValueError(msg)
            source_db = None
            file_content = source_file.content

    return {
        "id": source.id,
        "name": source.name,
        "type": source.type,
        "collection": source.collection,
        "source_db": source_db,
    }, file_content


@task(name="Index Source")
async def _index_source(source_id: int) -> list[str]:
    """Index source and route by source type.

    Args:
        source_id: The ID of the source to index.

    Returns:
        A list of text chunks indexed from the source.

    Raises:
        ValueError: If the source type is not supported.

    """
    source_data, file_content = await _load_source_data(source_id=source_id)

    collection = str(source_data["collection"])
    await ensure_collection(name=collection)

    source_type = source_data["type"]

    if source_type in SourceType.get_db_types():
        return await index_db_source(
            source_id=source_id,
            source_name=str(source_data["name"]),
            source_type=source_type,
            collection=collection,
            source_db=source_data["source_db"],
        )

    if file_content is None:
        msg = f"For source №{source_id} not found file content!"
        raise ValueError(msg)

    return await index_file_source(
        source_id=source_id,
        source_name=str(source_data["name"]),
        source_type=source_type,
        collection=collection,
        content=file_content,
    )


@task(name="Summarize Source")
async def _summarize_source(source_id: int, chunks: list[str]) -> str:
    """Summarize source chunks using active provider.

    Args:
        source_id: The ID of the source to summarize.
        chunks: The list of text chunks to summarize.

    Returns:
        The summary text.

    Raises:
        ValueError: If no active provider or models are found.

    """
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


@task(name="Complete Processing Source")
async def _complete_processing_source(source_id: int, summary: str) -> None:
    """Complete source processing by updating status and summary.

    Args:
        source_id: The ID of the source to complete processing for.
        summary: The summary text to update the source with.

    Raises:
        ValueError: If the source is not found.

    """
    repository = SourceRepository()

    async with async_session() as session:
        source = await repository.update_by(
            session=session,
            id=source_id,
            data={"status": SourceStatus.COMPLETED, "summary": summary},
        )
        if not source:
            msg = f"Source №{source_id} not found!"
            raise ValueError(msg)

    await upsert_chunks(
        collection=core_settings.sources_index_collection,
        ids=[f"source-{source.id}"],
        texts=[summary],
        payloads=[
            {
                "source_id": source.id,
                "source_name": source.name,
                "source_type": source.type.value,
            }
        ],
    )


@flow(name="Process Source", timeout_seconds=2 * 3600, retries=3)
async def process_source(source_id: int) -> None:
    """Process the source flow: index, summarize and complete processing.

    Args:
        source_id: The ID of the source to process.

    """
    chunks = await _index_source(source_id=source_id)

    summary = await _summarize_source(source_id=source_id, chunks=chunks)

    await _complete_processing_source(source_id=source_id, summary=summary)
