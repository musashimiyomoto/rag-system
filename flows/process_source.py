import base64
from pathlib import Path
from uuid import UUID

import chromadb
import textract
from chromadb.api.models.AsyncCollection import AsyncCollection
from langchain_text_splitters import RecursiveCharacterTextSplitter
from prefect import flow, task

from ai.summarize import summarize
from db.repositories import SourceRepository
from db.sessions import async_session
from enums.source import SourceStatus
from settings import BASE_PATH, chroma_settings, prefect_settings
from utils import redis_client

SOURCE_DIRECTORY = Path("sources")
SOURCE_DIRECTORY.mkdir(parents=True, exist_ok=True)


async def deploy_process_source_flow(source_id: int) -> UUID:
    """Deploy the process source flow.

    Args:
        source_id: The source ID.

    Returns:
        The deployment ID.

    """
    deployment = await flow.from_source(  # type: ignore[attr-defined]
        source=BASE_PATH, entrypoint="flows/process_source.py:process_source"
    )

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


async def get_source_filepath(source_id: int) -> tuple[str, Path]:
    """Get source filepath and save file from Redis to local storage.

    Args:
        source_id: The source ID.

    Returns:
        A tuple containing the collection name and file path.

    Raises:
        ValueError: If source is not found or file is not available in Redis.

    """
    repository = SourceRepository()

    async with async_session() as session:
        source = await repository.update_by(
            session=session,
            id=source_id,
            data={"status": SourceStatus.PROCESSED},
        )
        if not source:
            msg = f"Source №{source_id} not found!"
            raise ValueError(msg)

        collection_name = source.collection

        file = await redis_client.get(name=collection_name)
        if not file:
            await repository.update_by(
                session=session,
                id=source_id,
                data={"status": SourceStatus.FAILED},
            )
            msg = f"For source №{source_id} not found file!"
            raise ValueError(msg)

    filepath = SOURCE_DIRECTORY / f"{collection_name}.{source.type.value.lower()}"

    with filepath.open("wb") as buffer:
        buffer.write(base64.b64decode(file.encode("utf-8")))

    await redis_client.delete(collection_name)

    return collection_name, filepath


def _generate_chunks(filepath: Path, chunk_size: int = 512) -> list[str]:
    """Generate the file chunks.

    Args:
        filepath: The file path.
        chunk_size: The chunk size.

    Returns:
        The file chunks.

    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=0
    ).split_text(text=textract.process(filename=filepath.as_posix()).decode("utf-8"))


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
    collection_name, filepath = await get_source_filepath(source_id=source_id)

    collection = await get_or_create_collection(name=collection_name)

    chunks = _generate_chunks(filepath=filepath)

    await collection.add(
        ids=[str(i) for i in range(len(chunks))],
        documents=chunks,
    )

    filepath.unlink()

    return chunks


@task(name="Summarize Source")
async def _summarize_source(chunks: list[str]) -> str:
    """Summarize the source by processing all chunks.

    Args:
        chunks: The source chunks to summarize.

    Returns:
        The final source summary.

    """
    return await summarize(texts=chunks)


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

    summary = await _summarize_source(chunks=chunks)

    await _complete_processing_source(source_id=source_id, summary=summary)
