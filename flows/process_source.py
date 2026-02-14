from io import BytesIO
from uuid import UUID

import chromadb
from chromadb.api.models.AsyncCollection import AsyncCollection
from langchain_text_splitters import RecursiveCharacterTextSplitter
from prefect import flow, task
from pypdf import PdfReader

from ai.providers import list_provider_models
from ai.summarize import summarize
from constants import UTF8
from db.repositories import ProviderRepository, SourceFileRepository, SourceRepository
from db.sessions import async_session
from enums.source import SourceStatus, SourceType
from settings import BASE_PATH, chroma_settings, prefect_settings
from utils import decrypt


async def deploy_process_source_flow(source_id: int) -> UUID:
    """Deploy the process source flow.

    Args:
        source_id: The source ID.

    Returns:
        The deployment ID.

    """
    deployment = await flow.from_source(
        source=BASE_PATH, entrypoint="flows/process_source.py:process_source"
    )  # ty:ignore[invalid-await]

    return await deployment.deploy(
        name=f"PROCESS_SOURCE_{source_id}",
        work_pool_name=prefect_settings.pool_name,
        parameters={"source_id": source_id},
        concurrency_limit=1,
        print_next_steps=False,
        ignore_warnings=True,
    )


async def get_or_create_collection(name: str) -> AsyncCollection:
    """Get or create a ChromaDB collection.

    Args:
        name: The collection name.

    Returns:
        The ChromaDB collection instance.

    """
    client = await chromadb.AsyncHttpClient(
        host=chroma_settings.host,
        port=chroma_settings.port,
    )
    return await client.get_or_create_collection(name=name)


async def get_source_content(source_id: int) -> tuple[str, SourceType, bytes]:
    """Get source metadata and binary file content from PostgreSQL.

    Args:
        source_id: The source ID.

    Returns:
        A tuple containing collection name, source type and binary content.

    Raises:
        ValueError: If source or source file is not found.

    """
    source_repository = SourceRepository()
    source_file_repository = SourceFileRepository()

    async with async_session() as session:
        source = await source_repository.update_by(
            session=session,
            id=source_id,
            data={"status": SourceStatus.PROCESSED},
        )
        if not source:
            msg = f"Source №{source_id} not found!"
            raise ValueError(msg)

        source_file = await source_file_repository.get_by(
            session=session, source_id=source_id
        )
        if not source_file:
            await source_repository.update_by(
                session=session,
                id=source_id,
                data={"status": SourceStatus.FAILED},
            )
            msg = f"For source №{source_id} not found file!"
            raise ValueError(msg)

    return source.collection, source.type, source_file.content


def _extract_text(source_type: SourceType, content: bytes) -> str:
    """Extract UTF-8 text from source bytes without writing to disk.

    Args:
        source_type: The source type.
        content: Raw file content.

    Returns:
        Extracted text.

    """
    if source_type == SourceType.TXT:
        return content.decode(encoding=UTF8)

    if source_type == SourceType.PDF:
        return "\n".join(
            page.extract_text() or ""
            for page in PdfReader(stream=BytesIO(initial_bytes=content)).pages
        )

    msg = f"Unsupported source type: {source_type.value}"
    raise ValueError(msg)


def _generate_chunks(text: str, chunk_size: int = 512) -> list[str]:
    """Generate chunks from extracted text.

    Args:
        text: The extracted text to split into chunks.
        chunk_size: The maximum size of each chunk.

    Returns:
        A list of text chunks.

    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=0
    ).split_text(text=text)


@task(name="Complete Processing Source")
async def _complete_processing_source(source_id: int, summary: str) -> None:
    """Complete source processing by updating status and summary.

    Args:
        source_id: The source ID.
        summary: The source summary.

    """
    repository = SourceRepository()

    async with async_session() as session:
        await repository.update_by(
            session=session,
            id=source_id,
            data={"status": SourceStatus.COMPLETED, "summary": summary},
        )


@task(name="Index Source")
async def _index_source(source_id: int) -> list[str]:
    """Index the source by splitting it into chunks and storing in ChromaDB.

    Args:
        source_id: The source ID.

    Returns:
        List of source chunks.

    """
    collection_name, source_type, content = await get_source_content(
        source_id=source_id
    )

    collection = await get_or_create_collection(name=collection_name)

    chunks = _generate_chunks(
        text=_extract_text(source_type=source_type, content=content)
    )

    await collection.add(ids=[str(i) for i in range(len(chunks))], documents=chunks)

    return chunks


@task(name="Summarize Source")
async def _summarize_source(source_id: int, chunks: list[str]) -> str:
    """Summarize the source by processing all chunks.

    Args:
        source_id: The source ID.
        chunks: The source chunks to summarize.

    Returns:
        The final source summary.

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
        name=provider.name, api_key=decrypt(encrypted_data=provider.api_key_encrypted)
    )
    if len(models) > 0:
        model_name = models[0].name
    else:
        await source_repository.update_by(
            session=session, id=source_id, data={"status": SourceStatus.FAILED}
        )
        msg = f"No models found for provider {provider.name}!"
        raise ValueError(msg)

    return await summarize(
        texts=chunks,
        provider_name=provider.name,
        model_name=model_name,
        api_key_encrypted=provider.api_key_encrypted,
    )


@flow(name="Process Source", timeout_seconds=2 * 3600, retries=3)
async def process_source(source_id: int) -> None:
    """Process the source flow: index, summarize and complete processing.

    This flow handles the complete source processing pipeline:
    1. Index the source by splitting into chunks and storing in ChromaDB
    2. Summarize the source content
    3. Mark the source as completed with the summary

    Args:
        source_id: The source ID to process.

    """
    chunks = await _index_source(source_id=source_id)

    summary = await _summarize_source(source_id=source_id, chunks=chunks)

    await _complete_processing_source(source_id=source_id, summary=summary)
