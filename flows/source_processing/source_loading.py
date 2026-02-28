from db.repositories import SourceDbRepository, SourceFileRepository, SourceRepository
from db.sessions import async_session
from enums import SourceStatus, SourceType
from flows.source_processing.types import SourceProcessData


async def load_source_for_processing(
    source_id: int,
) -> tuple[SourceProcessData, bytes | None]:
    """Load source, set processed status and return source content context."""
    source_repository = SourceRepository()
    source_file_repository = SourceFileRepository()
    source_db_repository = SourceDbRepository()

    async with async_session() as session:
        source = await source_repository.update_by(
            session=session,
            id=source_id,
            data={"status": SourceStatus.PROCESSED},
        )
        if not source:
            msg = f"Source №{source_id} not found!"
            raise ValueError(msg)

        source_db = await source_db_repository.get_by(
            session=session, source_id=source_id
        )
        file_content = None
        if source.type in SourceType.get_db_types():
            if not source_db:
                await source_repository.update_by(
                    session=session,
                    id=source_id,
                    data={"status": SourceStatus.FAILED},
                )
                msg = f"For source №{source_id} not found source_db!"
                raise ValueError(msg)
        else:
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
            file_content = source_file.content

    return {
        "id": source.id,
        "name": source.name,
        "type": source.type,
        "collection": source.collection,
        "source_db": source_db,
    }, file_content
