from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import SessionSource
from db.repositories.base import BaseRepository


class SessionSourceRepository(BaseRepository[SessionSource]):
    def __init__(self):
        super().__init__(model=SessionSource)

    async def delete_many(
        self, session: AsyncSession, session_id: int, source_ids: list[int]
    ) -> None:
        if not source_ids:
            return

        await session.execute(
            delete(SessionSource).where(
                SessionSource.session_id == session_id,
                SessionSource.source_id.in_(source_ids),
            )
        )
        await session.commit()
