from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import db, provider
from schemas import (
    ProviderCreateRequest,
    ProviderModelResponse,
    ProviderResponse,
    ProviderUpdateRequest,
)

router = APIRouter(prefix="/provider", tags=["Provider"])


@router.post(path="")
async def create_provider(
    data: Annotated[ProviderCreateRequest, Body(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        provider.ProviderUsecase, Depends(dependency=provider.get_provider_usecase)
    ],
) -> ProviderResponse:
    return await usecase.create_provider(session=session, data=data)


@router.get(path="/list")
async def get_providers(
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        provider.ProviderUsecase, Depends(dependency=provider.get_provider_usecase)
    ],
) -> list[ProviderResponse]:
    return await usecase.get_providers(session=session)


@router.patch(path="/{provider_id}")
async def update_provider(
    provider_id: Annotated[int, Path(default=...)],
    data: Annotated[ProviderUpdateRequest, Body(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        provider.ProviderUsecase, Depends(dependency=provider.get_provider_usecase)
    ],
) -> ProviderResponse:
    return await usecase.update_provider(
        session=session, provider_id=provider_id, data=data
    )


@router.delete(path="/{provider_id}")
async def delete_provider(
    provider_id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        provider.ProviderUsecase, Depends(dependency=provider.get_provider_usecase)
    ],
) -> JSONResponse:
    await usecase.delete_provider(session=session, provider_id=provider_id)
    return JSONResponse(
        content={"detail": "Provider deleted successfully"},
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get(path="/{provider_id}/models")
async def get_provider_models(
    provider_id: Annotated[int, Path(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    usecase: Annotated[
        provider.ProviderUsecase, Depends(dependency=provider.get_provider_usecase)
    ],
) -> list[ProviderModelResponse]:
    return await usecase.get_provider_models(session=session, provider_id=provider_id)
