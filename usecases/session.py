from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import (
    MessageRepository,
    SessionRepository,
    SessionSourceRepository,
    SourceRepository,
)
from enums import SourceStatus
from exceptions import SessionConflictError, SourceNotFoundError
from schemas import SessionResponse


class SessionUsecase:
    def __init__(self):
        self._session_repository = SessionRepository()
        self._session_source_repository = SessionSourceRepository()
        self._source_repository = SourceRepository()
        self._message_repository = MessageRepository()

    async def create_session(
        self, session: AsyncSession, source_ids: list[int]
    ) -> SessionResponse:
        """Create a new session.

        Args:
            session: The async session.
            source_ids: The source ids.

        Returns:
            The created session.

        """
        for source_id in source_ids:
            source = await self._source_repository.get_by(session=session, id=source_id)

            if not source:
                raise SourceNotFoundError(message=f"Source #{source_id} not found")

            if source.status != SourceStatus.COMPLETED:
                msg = f"Source #{source_id} is not completed"
                raise SessionConflictError(message=msg)

        session_obj = await self._session_repository.create(session=session, data={})
        await self._session_source_repository.create_many(
            session=session,
            data=[
                {"session_id": session_obj.id, "source_id": source_id}
                for source_id in source_ids
            ],
        )

        return SessionResponse(
            id=session_obj.id, source_ids=source_ids, created_at=session_obj.created_at
        )

    async def delete_session(self, session: AsyncSession, session_id: int) -> None:
        """Delete a session.

        Args:
            session: The async session.
            session_id: The session id.

        """
        await self._message_repository.delete_all(
            session=session, session_id=session_id
        )
        await self._session_source_repository.delete_by(
            session=session, session_id=session_id
        )
        await self._session_repository.delete_by(session=session, id=session_id)
