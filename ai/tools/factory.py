from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Tool
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

from ai.tools.retrieve import retrieve
from enums import ToolId


@dataclass(frozen=True)
class ToolSpec:
    id: ToolId
    title: str
    description: str
    enabled_by_default: bool
    requires_sources: bool
    tool: Tool[Any] | Callable[..., Any]


TOOL_REGISTRY: dict[ToolId, ToolSpec] = {
    ToolId.RETRIEVE: ToolSpec(
        id=ToolId.RETRIEVE,
        title="Retrieve",
        description="Search through uploaded sources using vector similarity",
        enabled_by_default=True,
        requires_sources=True,
        tool=Tool(retrieve),
    ),
    ToolId.WEB_SEARCH: ToolSpec(
        id=ToolId.WEB_SEARCH,
        title="Web Search",
        description="Search the web using DuckDuckGo",
        enabled_by_default=True,
        requires_sources=False,
        tool=duckduckgo_search_tool(),
    ),
}


def get_tools(tool_ids: list[ToolId]) -> list[Tool[Any] | Callable[..., Any]]:
    """Get tools.

    Args:
        tool_ids: The tool_ids parameter.

    Returns:
        The list of callable tools for agent runtime.

    """
    tools: list[Tool[Any] | Callable[..., Any]] = []

    for tool_id in tool_ids:
        spec = TOOL_REGISTRY.get(tool_id)
        if not spec:
            continue

        tools.append(spec.tool)

    return tools
