from ai.tools import TOOL_REGISTRY
from schemas import ToolResponse


class ToolUsecase:
    async def get_tools(self) -> list[ToolResponse]:
        """Get tools.

        Returns:
            The list of available tool definitions.

        """
        return [
            ToolResponse(
                id=tool.id,
                title=tool.title,
                description=tool.description,
            )
            for tool in TOOL_REGISTRY.values()
        ]
