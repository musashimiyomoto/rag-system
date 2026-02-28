"""Helpers for loading file-source specific data for source processing flow."""

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import SourceFileRepository


async def load_source_file_content(
    session: AsyncSession, source_id: int
) -> bytes | None:
    """Load raw file content for a source id."""
    source_file = await SourceFileRepository().get_by(
        session=session, source_id=source_id
    )
    if source_file is None:
        return None

    return source_file.content
