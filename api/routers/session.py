from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import db, message, session
from schemas import MessageResponse, SessionRequest, SessionResponse

router = APIRouter(prefix="/session", tags=["Session"])


@router.post(path="")
async def create_session(
    data: Annotated[SessionRequest, Body(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        session.SessionUsecase, Depends(dependency=session.get_session_usecase)
    ],
) -> SessionResponse:
    return await usecase.create_session(session=session, source_id=data.source_id)


@router.get(path="/{session_id}/message/list")
async def get_messages(
    session_id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        message.MessageUsecase, Depends(dependency=message.get_message_usecase)
    ],
) -> list[MessageResponse]:
    return await usecase.get_messages(session=session, session_id=session_id)


@router.delete(path="/{session_id}")
async def delete_session(
    session_id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        session.SessionUsecase, Depends(dependency=session.get_session_usecase)
    ],
) -> JSONResponse:
    await usecase.delete_session(session=session, session_id=session_id)
    return JSONResponse(
        content={"detail": "Session deleted successfully"},
        status_code=status.HTTP_202_ACCEPTED,
    )
