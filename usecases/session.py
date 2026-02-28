from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import (
    MessageRepository,
    SessionRepository,
    SessionSourceRepository,
    SourceRepository,
)
from enums import SourceStatus
from exceptions import (
    SessionConflictError,
    SessionNotFoundError,
    SessionValidationError,
    SourceNotFoundError,
)
from schemas import SessionResponse


class SessionUsecase:
    def __init__(self):
        self._session_repository = SessionRepository()
        self._session_source_repository = SessionSourceRepository()
        self._source_repository = SourceRepository()
        self._message_repository = MessageRepository()

    async def _validate_source_ids(
        self, session: AsyncSession, source_ids: list[int]
    ) -> None:
        """Validate source ids.

        Args:
            session: The session parameter.
            source_ids: The source_ids parameter.

        """
        if len(source_ids) != len(set(source_ids)):
            raise SessionValidationError(message="Duplicate source IDs are not allowed")

        for source_id in source_ids:
            source = await self._source_repository.get_by(session=session, id=source_id)

            if not source:
                raise SourceNotFoundError(message=f"Source #{source_id} not found")

            if source.status != SourceStatus.COMPLETED:
                msg = f"Source #{source_id} is not completed"
                raise SessionConflictError(message=msg)

    async def _build_response(
        self, session: AsyncSession, session_id: int
    ) -> SessionResponse:
        """Build response.

        Args:
            session: The session parameter.
            session_id: The session_id parameter.

        Returns:
            The session response with attached source IDs.

        """
        chat_session = await self._session_repository.get_by(
            session=session, id=session_id
        )
        if not chat_session:
            raise SessionNotFoundError

        session_sources = await self._session_source_repository.get_all(
            session=session, session_id=session_id
        )
        source_ids = [item.source_id for item in session_sources]
        return SessionResponse(
            id=chat_session.id,
            source_ids=sorted(source_ids),
            created_at=chat_session.created_at,
        )

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
        await self._validate_source_ids(session=session, source_ids=source_ids)

        session_obj = await self._session_repository.create(session=session, data={})
        if source_ids:
            await self._session_source_repository.create_many(
                session=session,
                data=[
                    {"session_id": session_obj.id, "source_id": source_id}
                    for source_id in source_ids
                ],
            )

        return await self._build_response(session=session, session_id=session_obj.id)

    async def get_sessions(self, session: AsyncSession) -> list[SessionResponse]:
        """Get sessions.

        Args:
            session: The session parameter.

        Returns:
            The list of sessions ordered by creation time.

        """
        sessions = await self._session_repository.get_all(session=session)
        sorted_sessions = sorted(
            sessions,
            key=lambda item: (item.created_at, item.id),
            reverse=True,
        )
        return [
            await self._build_response(session=session, session_id=chat_session.id)
            for chat_session in sorted_sessions
        ]

    async def update_session_sources(
        self, session: AsyncSession, session_id: int, source_ids: list[int]
    ) -> SessionResponse:
        """Update session sources.

        Args:
            session: The session parameter.
            session_id: The session_id parameter.
            source_ids: The source_ids parameter.

        Returns:
            The updated session response.

        """
        chat_session = await self._session_repository.get_by(
            session=session, id=session_id
        )
        if not chat_session:
            raise SessionNotFoundError

        await self._validate_source_ids(session=session, source_ids=source_ids)

        current_links = await self._session_source_repository.get_all(
            session=session, session_id=session_id
        )
        current_ids = {link.source_id for link in current_links}
        new_ids = set(source_ids)

        to_add = sorted(new_ids - current_ids)
        to_remove = sorted(current_ids - new_ids)

        if to_remove:
            await self._session_source_repository.delete_many(
                session=session, session_id=session_id, source_ids=to_remove
            )
        if to_add:
            await self._session_source_repository.create_many(
                session=session,
                data=[
                    {"session_id": session_id, "source_id": source_id}
                    for source_id in to_add
                ],
            )

        return await self._build_response(session=session, session_id=session_id)

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
