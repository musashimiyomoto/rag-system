from db.repositories import SourceRepository
from db.sessions import async_session
from enums import SourceStatus, SourceType
from flows.db_processing.loading import load_source_db
from flows.file_processing.loading import load_source_file_content
from flows.types import SourceProcessData


async def load_source_for_processing(
    source_id: int,
) -> tuple[SourceProcessData, bytes | None]:
    """Load source context and branch-specific payload for processing."""
    source_repository = SourceRepository()

    async with async_session() as session:
        source = await source_repository.update_by(
            session=session,
            id=source_id,
            data={"status": SourceStatus.PROCESSED},
        )
        if not source:
            msg = f"Source №{source_id} not found!"
            raise ValueError(msg)

        file_content = None
        if source.type in SourceType.get_db_types():
            source_db = await load_source_db(session=session, source_id=source_id)
            if source_db is None:
                await source_repository.update_by(
                    session=session,
                    id=source_id,
                    data={"status": SourceStatus.FAILED},
                )
                msg = f"For source №{source_id} not found source_db!"
                raise ValueError(msg)
        else:
            file_content = await load_source_file_content(
                session=session, source_id=source_id
            )
            if file_content is None:
                await source_repository.update_by(
                    session=session,
                    id=source_id,
                    data={"status": SourceStatus.FAILED},
                )
                msg = f"For source №{source_id} not found file!"
                raise ValueError(msg)
            source_db = None

    return {
        "id": source.id,
        "name": source.name,
        "type": source.type,
        "collection": source.collection,
        "source_db": source_db,
    }, file_content
