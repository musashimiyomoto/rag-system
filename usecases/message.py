from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import MessageRepository
from schemas import MessageResponse


class MessageUsecase:
    def __init__(self):
        self._message_repository = MessageRepository()

    async def get_messages(
        self, session: AsyncSession, session_id: int
    ) -> list[MessageResponse]:
        """Get the messages.

        Args:
            session: The async session.
            session_id: The session id.

        Returns:
            The list of messages.

        """
        return [
            MessageResponse.model_validate(message)
            for message in await self._message_repository.get_all(
                session=session, session_id=session_id
            )
        ]
