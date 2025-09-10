from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Path, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import db, document, session
from schemas import DocumentResponse, SessionResponse

router = APIRouter(prefix="/document", tags=["Document"])


@router.post(path="")
async def create_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        document.DocumentUsecase, Depends(dependency=document.get_document_usecase)
    ],
) -> DocumentResponse:
    document = await usecase.create_document(
        session=session, file=file.file, file_size=file.size, filename=file.filename
    )

    background_tasks.add_task(
        usecase.deploy_process_document_flow, document_id=document.id
    )

    return document


@router.get(path="/list")
async def get_documents(
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        document.DocumentUsecase, Depends(dependency=document.get_document_usecase)
    ],
) -> list[DocumentResponse]:
    return await usecase.get_documents(session=session)


@router.get(path="/{document_id}")
async def get_document(
    document_id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        document.DocumentUsecase, Depends(dependency=document.get_document_usecase)
    ],
) -> DocumentResponse:
    return await usecase.get_document(session=session, document_id=document_id)


@router.get(path="/{document_id}/session/list")
async def get_sessions_for_document(
    document_id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        session.SessionUsecase, Depends(dependency=session.get_session_usecase)
    ],
) -> list[SessionResponse]:
    return await usecase.get_sessions_for_document(
        session=session, document_id=document_id
    )


@router.delete(path="/{id}")
async def delete_document(
    id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        document.DocumentUsecase, Depends(dependency=document.get_document_usecase)
    ],
) -> JSONResponse:
    await usecase.delete_document(session=session, id=id)
    return JSONResponse(
        content={"detail": "Document deleted successfully"},
        status_code=status.HTTP_202_ACCEPTED,
    )
