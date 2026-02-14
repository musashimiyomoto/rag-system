from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import MessageRepository, SessionRepository
from schemas import SessionResponse


class SessionUsecase:
    def __init__(self):
        self._session_repository = SessionRepository()
        self._message_repository = MessageRepository()

    async def create_session(
        self, session: AsyncSession, source_id: int
    ) -> SessionResponse:
        """Create a new session.

        Args:
            session: The async session.
            source_id: The source id.

        Returns:
            The created session.

        """
        return SessionResponse.model_validate(
            await self._session_repository.create(
                session=session,
                data={
                    "source_id": source_id,
                },
            )
        )

    async def get_sessions_for_source(
        self, session: AsyncSession, source_id: int
    ) -> list[SessionResponse]:
        """Get sessions for a source.

        Args:
            session: The async session.
            source_id: The source id.

        Returns:
            The list of sessions.

        """
        return [
            SessionResponse.model_validate(session_obj)
            for session_obj in await self._session_repository.get_all(
                session=session, source_id=source_id
            )
        ]

    async def delete_session(self, session: AsyncSession, session_id: int) -> None:
        """Delete a session.

        Args:
            session: The async session.
            session_id: The session id.

        """
        await self._message_repository.delete_all(
            session=session, session_id=session_id
        )
        await self._session_repository.delete_by(session=session, id=session_id)
