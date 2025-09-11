import base64
from pathlib import Path
from uuid import UUID

import chromadb
import textract
from chromadb.api.models.AsyncCollection import AsyncCollection
from langchain_text_splitters import RecursiveCharacterTextSplitter
from prefect import flow, task

from ai.summarize import summarize
from db.repositories import DocumentRepository
from db.sessions import async_session
from enums.document import DocumentStatus
from settings import BASE_PATH, chroma_settings, prefect_settings
from utils import redis_client

DOCUMENT_DIRECTORY = Path("documents")
DOCUMENT_DIRECTORY.mkdir(parents=True, exist_ok=True)


async def deploy_process_document_flow(document_id: int) -> UUID:
    """Deploy the process document flow.

    Args:
        document_id: The document ID.

    Returns:
        The deployment ID.

    """
    deployment = await flow.from_source(  # type: ignore[attr-defined]
        source=BASE_PATH, entrypoint="flows/process_document.py:process_document"
    )

    return await deployment.deploy(  # type: ignore[attr-defined]
        name=f"PROCESS_DOCUMENT_{document_id}",
        work_pool_name=prefect_settings.pool_name,
        parameters={"document_id": document_id},
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


async def get_document_filepath(document_id: int) -> tuple[str, Path]:
    """Get document filepath and save file from Redis to local storage.

    Args:
        document_id: The document ID.

    Returns:
        A tuple containing the collection name and file path.

    Raises:
        ValueError: If document is not found or file is not available in Redis.

    """
    repository = DocumentRepository()

    async with async_session() as session:
        document = await repository.update_by(
            session=session,
            id=document_id,
            data={"status": DocumentStatus.PROCESSED},
        )
        if not document:
            msg = f"Document №{document_id} not found!"
            raise ValueError(msg)

        collection_name = document.collection

        file = await redis_client.get(name=collection_name)
        if not file:
            await repository.update_by(
                session=session,
                id=document_id,
                data={"status": DocumentStatus.FAILED},
            )
            msg = f"For document №{document_id} not found file!"
            raise ValueError(msg)

    filepath = DOCUMENT_DIRECTORY / f"{collection_name}.{document.type.value.lower()}"

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


@task(name="Complete Processing Document")
async def _complete_processing_document(document_id: int, summary: str) -> None:
    """Complete document processing by updating status and summary.

    Args:
        document_id: The document ID.
        summary: The document summary.

    """
    repository = DocumentRepository()

    async with async_session() as session:
        await repository.update_by(
            session=session,
            id=document_id,
            data={"status": DocumentStatus.COMPLETED, "summary": summary},
        )


@task(name="Index Document")
async def _index_document(document_id: int) -> list[str]:
    """Index the document by splitting it into chunks and storing in ChromaDB.

    Args:
        document_id: The document ID.

    Returns:
        List of document chunks.

    """
    collection_name, filepath = await get_document_filepath(document_id=document_id)

    collection = await get_or_create_collection(name=collection_name)

    chunks = _generate_chunks(filepath=filepath)

    await collection.add(
        ids=[str(i) for i in range(len(chunks))],
        documents=chunks,
    )

    filepath.unlink()

    return chunks


@task(name="Summarize Document")
async def _summarize_document(chunks: list[str]) -> str:
    """Summarize the document by processing all chunks.

    Args:
        chunks: The document chunks to summarize.

    Returns:
        The final document summary.

    """
    summary = ""
    for chunk in chunks:
        summary += await summarize(text=chunk)

    return await summarize(text=summary)


@flow(name="Process Document", timeout_seconds=2 * 3600, retries=3)
async def process_document(document_id: int) -> None:
    """Process the document flow: index, summarize and complete processing.

    This flow handles the complete document processing pipeline:
    1. Index the document by splitting into chunks and storing in ChromaDB
    2. Summarize the document content
    3. Mark the document as completed with the summary

    Args:
        document_id: The document ID to process.

    """
    chunks = await _index_document(document_id=document_id)

    summary = await _summarize_document(chunks=chunks)

    await _complete_processing_document(document_id=document_id, summary=summary)
