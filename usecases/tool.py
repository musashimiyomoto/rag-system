from ai.tools import TOOL_REGISTRY
from schemas import ToolResponse


class ToolUsecase:
    async def get_tools(self) -> list[ToolResponse]:
        return [ToolResponse.model_validate(tool) for tool in TOOL_REGISTRY.values()]
