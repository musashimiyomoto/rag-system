from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import AgentDeps
from api.dependencies import agent, chat, db
from constants import MEDIA_TYPE
from enums import ToolId
from schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/stream")
async def chat_stream(
    data: Annotated[ChatRequest, Body(default=...)],
    provider_id: Annotated[int, Query(default=..., gt=0)],
    model_name: Annotated[str, Query(default=..., min_length=1)],
    tool_ids: Annotated[list[ToolId], Query(default_factory=list)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    agent: Annotated[agent.Agent[AgentDeps, str], Depends(dependency=agent.get_agent)],
    usecase: Annotated[chat.ChatUsecase, Depends(dependency=chat.get_chat_usecase)],
) -> StreamingResponse:
    return StreamingResponse(
        content=usecase.stream_messages(
            data=data,
            session=session,
            agent=agent,
            provider_id=provider_id,
            model_name=model_name,
            tool_ids=tool_ids,
        ),
        media_type=MEDIA_TYPE,
    )
