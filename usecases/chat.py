import json
from datetime import datetime
from typing import Any, AsyncGenerator

from pydantic_ai import Agent
from pydantic_ai.messages import (
    FunctionToolResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    PartDeltaEvent,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ToolReturnPart,
    UserPromptPart,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import AgentDeps, RetrieveContext
from db.repositories import (
    MessageRepository,
    SessionRepository,
    SessionSourceRepository,
)
from enums import Role, ToolId
from exceptions import SessionNotFoundError, SessionValidationError
from schemas import ChatRequest, ChatResponse, RetrieveToolRequest


class ChatUsecase:
    def __init__(self):
        self._message_repository = MessageRepository()
        self._session_repository = SessionRepository()
        self._session_source_repository = SessionSourceRepository()

    async def get_session_source_ids(
        self, session: AsyncSession, session_id: int
    ) -> list[int]:
        """Get source IDs attached to a chat session."""
        session_sources = await self._session_source_repository.get_all(
            session=session, session_id=session_id
        )
        return [session_source.source_id for session_source in session_sources]

    @staticmethod
    def get_tool_ids(data: ChatRequest) -> list[ToolId]:
        """Get ordered tool IDs from the request."""
        return [tool.id for tool in data.tools]

    @staticmethod
    def get_retrieve_source_ids(data: ChatRequest) -> list[int] | None:
        """Get retrieve source IDs from the request."""
        for tool in data.tools:
            if isinstance(tool, RetrieveToolRequest):
                return tool.source_ids
        return None

    @staticmethod
    def validate_retrieve_sources(
        session_source_ids: list[int], retrieve_source_ids: list[int] | None
    ) -> None:
        """Validate retrieve source IDs against session source IDs."""
        if retrieve_source_ids is None:
            return

        session_source_set = set(session_source_ids)
        for source_id in retrieve_source_ids:
            if source_id not in session_source_set:
                msg = (
                    f"Source #{source_id} is not attached to session. "
                    "Attach it to the session first."
                )
                raise SessionValidationError(message=msg)

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
        results: list[ModelMessage] = []
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
        data: ChatRequest,
        thinking: str | None = None,
    ) -> None:
        """Save the message to the history.

        Args:
            session: The async session.
            session_id: The session id.
            messages: The messages.
            data: The chat request data.
            thinking: The thinking text captured from tool stream.

        """
        records = []
        tool_ids = self.get_tool_ids(data=data)
        current_time = datetime.now()

        for message in messages:
            if len(message.parts) == 0:
                continue

            first_part = message.parts[0]
            if isinstance(message, ModelRequest):
                if isinstance(first_part, UserPromptPart):
                    records.append(
                        {
                            "role": Role.USER,
                            "session_id": session_id,
                            "content": first_part.content,
                            "timestamp": current_time,
                            "provider_id": data.provider_id,
                            "model_name": data.model_name,
                            "tool_ids": tool_ids,
                        }
                    )
            elif isinstance(message, ModelResponse) and isinstance(
                first_part, TextPart
            ):
                records.append(
                    {
                        "role": Role.AGENT,
                        "session_id": session_id,
                        "content": first_part.content,
                        "timestamp": current_time,
                        "thinking": thinking,
                        "provider_id": data.provider_id,
                        "model_name": data.model_name,
                        "tool_ids": tool_ids,
                    }
                )

        await self._message_repository.create_many(session=session, data=records)

    @staticmethod
    def _merge_stream_text(current_text: str, chunk_text: str) -> str:
        """Merge streamed text chunks into one deterministic string.

        Args:
            current_text: The current full text before merging.
            chunk_text: The new text chunk to merge.

        Returns:
            The merged full text after merging the new chunk.

        """
        if not chunk_text:
            return current_text
        if chunk_text == current_text:
            return current_text
        if chunk_text.startswith(current_text):
            return chunk_text
        if current_text.endswith(chunk_text):
            return current_text
        return current_text + chunk_text

    @staticmethod
    def _extract_text_chunk(event: Any) -> str | None:
        """Extract text chunk from pydantic-ai stream event.

        Args:
            event: The stream event.

        Returns:
            The text chunk if the event is a text part delta, otherwise None.

        """
        if not isinstance(event, PartDeltaEvent):
            return None

        if not isinstance(event.delta, TextPartDelta):
            return None

        return event.delta.content_delta

    @staticmethod
    def _normalize_tool_content(content: Any) -> str:
        """Normalize tool result content to a stable string.

        Args:
            content: The original tool result content, which can be of any type.

        Returns:
            The normalized string content.

        """
        if isinstance(content, str):
            return content
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="ignore")
        if isinstance(content, (dict, list)):
            return json.dumps(content, sort_keys=True)
        return str(content)

    @classmethod
    def _extract_deep_think_chunk(cls, event: Any) -> str | None:
        """Extract deep_think tool output chunk from stream event.

        Args:
            event: The stream event.

        Returns:
            The thinking chunk if the event is a deep_think tool output, otherwise None.

        """
        if not isinstance(event, FunctionToolResultEvent):
            return None
        if not isinstance(event.result, ToolReturnPart):
            return None
        if event.result.tool_name != ToolId.DEEP_THINK:
            return None
        return cls._normalize_tool_content(event.result.content)

    async def stream_messages(
        self, data: ChatRequest, session: AsyncSession, agent: Agent[AgentDeps, str]
    ) -> AsyncGenerator[bytes, None]:
        """Stream the messages.

        Args:
            data: The chat request.
            session: The async session.
            agent: The agent.

        Yields:
            The bytes of the messages.

        """
        chat_session = await self._session_repository.get_by(
            session=session, id=data.session_id
        )
        if not chat_session:
            raise SessionNotFoundError

        session_source_ids = await self.get_session_source_ids(
            session=session, session_id=data.session_id
        )
        retrieve_source_ids = self.get_retrieve_source_ids(data=data)
        self.validate_retrieve_sources(
            session_source_ids=session_source_ids,
            retrieve_source_ids=retrieve_source_ids,
        )

        tool_ids = self.get_tool_ids(data=data)

        yield ChatResponse(
            role=Role.USER,
            timestamp=datetime.now(),
            content=data.message,
            provider_id=data.provider_id,
            model_name=data.model_name,
            tool_ids=tool_ids,
        ).model_dump_bytes()

        run_result = None
        thinking = ""

        async for event in agent.run_stream_events(
            user_prompt=data.message,
            deps=AgentDeps(
                session=session,
                session_id=data.session_id,
                session_source_ids=session_source_ids,
                retrieve_context=(
                    RetrieveContext(source_ids=retrieve_source_ids)
                    if retrieve_source_ids is not None
                    else None
                ),
            ),
            message_history=await self.get_message_history(
                session=session, session_id=data.session_id
            ),
        ):
            text_chunk = self._extract_text_chunk(event=event)
            if text_chunk is not None:
                yield ChatResponse(
                    role=Role.AGENT,
                    timestamp=datetime.now(),
                    content=text_chunk,
                    provider_id=data.provider_id,
                    model_name=data.model_name,
                    tool_ids=tool_ids,
                ).model_dump_bytes()

            thinking_chunk = self._extract_deep_think_chunk(event=event)
            if thinking_chunk is not None:
                thinking = self._merge_stream_text(
                    current_text=thinking,
                    chunk_text=thinking_chunk,
                )
                yield ChatResponse(
                    role=Role.AGENT,
                    timestamp=datetime.now(),
                    content="",
                    thinking=thinking_chunk,
                    provider_id=data.provider_id,
                    model_name=data.model_name,
                    tool_ids=tool_ids,
                ).model_dump_bytes()

            if getattr(event, "event_kind", None) == "agent_run_result":
                run_result = getattr(event, "result", None)

        if run_result is None:
            return

        await self.save_message_history(
            session=session,
            session_id=data.session_id,
            messages=run_result.new_messages(),
            data=data,
            thinking=thinking,
        )
