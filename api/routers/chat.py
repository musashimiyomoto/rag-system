from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import AgentDeps
from api.dependencies import agent, chat, db
from constants import MEDIA_TYPE
from schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(path="/stream")
async def chat_stream(
    data: Annotated[ChatRequest, Body(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    agent: Annotated[agent.Agent[AgentDeps, str], Depends(dependency=agent.get_agent)],
    usecase: Annotated[chat.ChatUsecase, Depends(dependency=chat.get_chat_usecase)],
) -> StreamingResponse:
    return StreamingResponse(
        content=usecase.stream_messages(data=data, session=session, agent=agent),
        media_type=MEDIA_TYPE,
    )
