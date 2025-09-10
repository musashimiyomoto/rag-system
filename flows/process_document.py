import base64
from pathlib import Path
from uuid import UUID

import chromadb
import textract
from chromadb.api.models.AsyncCollection import AsyncCollection
from langchain_text_splitters import RecursiveCharacterTextSplitter
from prefect import flow, task

from ai.summarize import summarize
from constants import SUMMART_COLLECTION
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
    """Get the collection.

    Args:
        name: The collection name.

    """
    client = await chromadb.AsyncHttpClient(
        host=chroma_settings.host,
        port=chroma_settings.port,
    )
    return await client.get_or_create_collection(name=name)


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


@task(name="Index Document")
async def _index_document(filepath: Path, document_collection: str) -> list[str]:
    """Index the document.

    Args:
        filepath: The file path.
        document_collection: The document collection name.

    """
    collection = await get_or_create_collection(name=document_collection)

    chunks = _generate_chunks(filepath=filepath)

    await collection.add(
        ids=[str(i) for i in range(len(chunks))],
        documents=chunks,
    )

    return chunks


@task(name="Summarize Document")
async def _summarize_document(chunks: list[str]) -> str:
    """Summarize the document.

    Args:
        chunks: The chunks.

    """
    summary = ""
    for chunk in chunks:
        summary += await summarize(text=chunk)

    return await summarize(text=summary)


@task(name="Index Summary")
async def _index_summary(summary: str, document_collection: str) -> None:
    """Index the summary.

    Args:
        summary: The summary.
        document_collection: The document collection.

    """
    collection = await get_or_create_collection(name=SUMMART_COLLECTION)

    await collection.add(ids=[document_collection], documents=[summary])


@flow(name="Process Document", timeout_seconds=2 * 3600, retries=3)
async def process_document(document_id: int) -> None:
    """Process the document flow.

    Args:
        document_id: The document ID.

    """
    repository = DocumentRepository()

    async with async_session() as session:
        document = await repository.update_by(
            session=session,
            id=document_id,
            data={"status": DocumentStatus.PROCESSED},
        )
        if not document:
            await repository.update_by(
                session=session,
                id=document_id,
                data={"status": DocumentStatus.FAILED},
            )
            return

        file = await redis_client.get(name=document.collection)
        if not file:
            await repository.update_by(
                session=session,
                id=document_id,
                data={"status": DocumentStatus.FAILED},
            )
            return

        filepath = (
            DOCUMENT_DIRECTORY / f"{document.collection}.{document.type.value.lower()}"
        )
        with filepath.open("wb") as buffer:
            buffer.write(base64.b64decode(file.encode("utf-8")))

        await redis_client.delete(document.collection)

        chunks = await _index_document(
            filepath=filepath,
            document_collection=document.collection,
        )

        summary = await _summarize_document(chunks=chunks)

        await _index_summary(summary=summary, document_collection=document.collection)

        await repository.update_by(
            session=session,
            id=document_id,
            data={"status": DocumentStatus.COMPLETED, "summary": summary},
        )
