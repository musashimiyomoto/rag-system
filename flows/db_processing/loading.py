"""Helpers for loading DB-source specific data for source processing flow."""

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import SourceDb
from db.repositories import SourceDbRepository


async def load_source_db(session: AsyncSession, source_id: int) -> SourceDb | None:
    """Load DB source configuration for a source id."""
    return await SourceDbRepository().get_by(session=session, source_id=source_id)
