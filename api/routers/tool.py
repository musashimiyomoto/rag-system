from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import tool
from schemas import ToolResponse

router = APIRouter(prefix="/tool", tags=["Tool"])


@router.get(path="/list")
async def get_tools(
    usecase: Annotated[tool.ToolUsecase, Depends(dependency=tool.get_tool_usecase)],
) -> list[ToolResponse]:
    return await usecase.get_tools()
