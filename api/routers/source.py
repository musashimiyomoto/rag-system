from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Path, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import db, session, source
from schemas import SessionResponse, SourceResponse

router = APIRouter(prefix="/source", tags=["Source"])


@router.post(path="")
async def create_source(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        source.SourceUsecase, Depends(dependency=source.get_source_usecase)
    ],
) -> SourceResponse:
    source = await usecase.create_source(
        session=session, file=file.file, file_size=file.size, filename=file.filename
    )

    background_tasks.add_task(usecase.deploy_process_source_flow, source_id=source.id)

    return source


@router.get(path="/list")
async def get_sources(
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        source.SourceUsecase, Depends(dependency=source.get_source_usecase)
    ],
) -> list[SourceResponse]:
    return await usecase.get_sources(session=session)


@router.get(path="/{source_id}")
async def get_source(
    source_id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        source.SourceUsecase, Depends(dependency=source.get_source_usecase)
    ],
) -> SourceResponse:
    return await usecase.get_source(session=session, source_id=source_id)


@router.get(path="/{source_id}/session/list")
async def get_sessions_for_source(
    source_id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        session.SessionUsecase, Depends(dependency=session.get_session_usecase)
    ],
) -> list[SessionResponse]:
    return await usecase.get_sessions_for_source(session=session, source_id=source_id)


@router.delete(path="/{id}")
async def delete_source(
    id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        source.SourceUsecase, Depends(dependency=source.get_source_usecase)
    ],
) -> JSONResponse:
    await usecase.delete_source(session=session, id=id)
    return JSONResponse(
        content={"detail": "Source deleted successfully"},
        status_code=status.HTTP_202_ACCEPTED,
    )
