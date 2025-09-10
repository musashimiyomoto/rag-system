from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.dependencies import health
from schemas import HealthResponse, ServiceHealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(path="/liveness")
async def liveness() -> JSONResponse:
    return JSONResponse(content={"status": True})


@router.get(path="/readiness")
async def readiness(
    usecase: Annotated[health.HealthUsecase, Depends(health.get_health_usecase)],
) -> HealthResponse:
    health = await usecase.health()
    return HealthResponse(
        services=[
            ServiceHealthResponse(name=name, status=status)
            for name, status in health.items()
        ]
    )
