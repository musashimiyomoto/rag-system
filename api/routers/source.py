from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Path,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import db, source
from schemas import (
    DbSourceCreateRequest,
    DbSourceIntrospectRequest,
    DbSourceIntrospectResponse,
    SourceResponse,
)

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


@router.post(path="/db/introspect")
async def introspect_db_source(
    data: Annotated[DbSourceIntrospectRequest, Body(default=...)],
    usecase: Annotated[
        source.SourceUsecase, Depends(dependency=source.get_source_usecase)
    ],
) -> DbSourceIntrospectResponse:
    return await usecase.introspect_db_source(data=data)


@router.post(path="/db")
async def create_db_source(
    background_tasks: BackgroundTasks,
    data: Annotated[DbSourceCreateRequest, Body(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        source.SourceUsecase, Depends(dependency=source.get_source_usecase)
    ],
) -> SourceResponse:
    source = await usecase.create_db_source(session=session, data=data)

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


@router.get(path="/type/list")
async def get_source_types(
    usecase: Annotated[
        source.SourceUsecase, Depends(dependency=source.get_source_usecase)
    ],
) -> list[str]:
    return usecase.get_supported_source_types()


@router.get(path="/{source_id}")
async def get_source(
    source_id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        source.SourceUsecase, Depends(dependency=source.get_source_usecase)
    ],
) -> SourceResponse:
    return await usecase.get_source(session=session, source_id=source_id)


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
