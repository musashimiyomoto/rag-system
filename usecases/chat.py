from datetime import datetime
from typing import AsyncGenerator

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    UserPromptPart,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import Dependencies
from ai.prompts import SYSTEM_PROMPT
from db.repositories import (
    MessageRepository,
    SessionRepository,
    SessionSourceRepository,
    SourceRepository,
)
from enums import Role, ToolId
from exceptions import SessionNotFoundError
from schemas import ChatRequest, ChatResponse


class ChatUsecase:
    def __init__(self):
        self._message_repository = MessageRepository()
        self._session_repository = SessionRepository()
        self._session_source_repository = SessionSourceRepository()
        self._source_repository = SourceRepository()

    async def get_message_history(
        self, session: AsyncSession, session_id: int
    ) -> list[ModelMessage]:
        """Get the message history.

        Args:
            session: The async session.
            session_id: The session id.

        Returns:
            The list of model messages.

        """
        results: list[ModelMessage] = [
            ModelRequest(parts=[SystemPromptPart(content=SYSTEM_PROMPT)]),
        ]
        for message in await self._message_repository.get_all(
            session=session, session_id=session_id
        ):
            if message.role == Role.USER:
                results.append(
                    ModelRequest(parts=[UserPromptPart(content=message.content)])
                )
            elif message.role == Role.AGENT:
                parts: list[ModelResponsePart] = [TextPart(content=message.content)]
                if message.thinking:
                    parts.append(ThinkingPart(content=message.thinking))
                results.append(ModelResponse(parts=parts))
            else:
                msg = f"Invalid role: {message.role}"
                raise ValueError(msg)

        return results

    async def save_message_history(
        self,
        session: AsyncSession,
        session_id: int,
        messages: list[ModelMessage],
        provider_id: int,
        model_name: str,
        tool_ids: list[ToolId],
    ) -> None:
        """Save the message to the history.

        Args:
            session: The async session.
            session_id: The session id.
            messages: The messages.

        """
        data = []
        current_time = datetime.now()

        for message in messages:
            first_part = message.parts[0]
            second_part = message.parts[1] if len(message.parts) > 1 else None
            if isinstance(message, ModelRequest):
                if isinstance(first_part, UserPromptPart):
                    data.append(
                        {
                            "role": Role.USER,
                            "session_id": session_id,
                            "content": first_part.content,
                            "timestamp": current_time,
                            "provider_id": provider_id,
                            "model_name": model_name,
                            "tool_ids": tool_ids,
                        }
                    )
                elif isinstance(first_part, SystemPromptPart) and isinstance(
                    second_part, UserPromptPart
                ):
                    data.append(
                        {
                            "role": Role.AGENT,
                            "session_id": session_id,
                            "content": second_part.content,
                            "timestamp": current_time,
                            "provider_id": provider_id,
                            "model_name": model_name,
                            "tool_ids": tool_ids,
                        }
                    )
            elif isinstance(message, ModelResponse) and isinstance(
                first_part, TextPart
            ):
                data.append(
                    {
                        "role": Role.AGENT,
                        "session_id": session_id,
                        "content": first_part.content,
                        "timestamp": current_time,
                        "thinking": (
                            second_part.content
                            if isinstance(second_part, ThinkingPart)
                            else None
                        ),
                        "provider_id": provider_id,
                        "model_name": model_name,
                        "tool_ids": tool_ids,
                    }
                )

        await self._message_repository.create_many(session=session, data=data)

    async def stream_messages(
        self,
        data: ChatRequest,
        session: AsyncSession,
        agent: Agent[Dependencies, str],
        provider_id: int,
        model_name: str,
        tool_ids: list[ToolId],
    ) -> AsyncGenerator[bytes, None]:
        """Stream the messages.

        Args:
            data: The chat request.
            session: The async session.
            agent: The agent.

        Yields:
            The bytes of the messages.

        """
        yield ChatResponse(
            role=Role.USER,
            timestamp=datetime.now(),
            content=data.message,
            provider_id=provider_id,
            model_name=model_name,
            tool_ids=tool_ids,
        ).model_dump_bytes()

        chat_session = await self._session_repository.get_by(
            session=session, id=data.session_id
        )
        if not chat_session:
            raise SessionNotFoundError

        source_ids = [
            source_session.source_id
            for source_session in await self._session_source_repository.get_all(
                session=session, session_id=data.session_id
            )
        ]

        async with agent.run_stream(
            data.message,
            deps=Dependencies(session=session, source_ids=source_ids),
            message_history=await self.get_message_history(
                session=session, session_id=data.session_id
            ),
        ) as result:
            async for chunk in result.stream_output():
                yield ChatResponse(
                    role=Role.AGENT,
                    timestamp=result.timestamp(),
                    content=chunk,
                    provider_id=provider_id,
                    model_name=model_name,
                    tool_ids=tool_ids,
                ).model_dump_bytes()

        await self.save_message_history(
            session=session,
            session_id=data.session_id,
            messages=result.new_messages(),
            provider_id=provider_id,
            model_name=model_name,
            tool_ids=tool_ids,
        )
