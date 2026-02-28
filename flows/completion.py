from prefect import task

from ai.vector_store import upsert_chunks
from db.repositories import SourceRepository
from db.sessions import async_session
from enums import SourceStatus
from settings import core_settings


@task(name="Complete Processing Source")
async def _complete_processing_source(source_id: int, summary: str) -> None:
    """Complete source processing by updating status and summary."""
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
