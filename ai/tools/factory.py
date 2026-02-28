from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Tool
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

from ai.tools.retrieve import retrieve
from enums import ToolId, ToolRuntimeRequirement


@dataclass(frozen=True)
class ToolSpec:
    id: ToolId
    title: str
    description: str
    enabled_by_default: bool
    requires_sources: bool
    runtime_requirements: set[ToolRuntimeRequirement]
    tool: Tool[Any] | Callable[..., Any]


TOOL_REGISTRY: dict[ToolId, ToolSpec] = {
    ToolId.RETRIEVE: ToolSpec(
        id=ToolId.RETRIEVE,
        title="Retrieve",
        description="Search through uploaded sources using vector similarity",
        enabled_by_default=True,
        requires_sources=True,
        runtime_requirements={
            ToolRuntimeRequirement.SESSION,
            ToolRuntimeRequirement.SOURCES,
            ToolRuntimeRequirement.RETRIEVE_CONFIG,
        },
        tool=Tool(retrieve),
    ),
    ToolId.WEB_SEARCH: ToolSpec(
        id=ToolId.WEB_SEARCH,
        title="Web Search",
        description="Search the web using DuckDuckGo",
        enabled_by_default=True,
        requires_sources=False,
        runtime_requirements=set(),
        tool=duckduckgo_search_tool(),
    ),
}


def get_default_tool_ids() -> list[ToolId]:
    """Get default tool ids.

    Returns:
        The list of tool IDs enabled by default.

    """
    return [
        tool_id for tool_id, spec in TOOL_REGISTRY.items() if spec.enabled_by_default
    ]


def get_tools(tool_ids: list[ToolId]) -> list[Tool[Any] | Callable[..., Any]]:
    """Get tools.

    Args:
        tool_ids: The tool_ids parameter.

    Returns:
        The list of callable tools for agent runtime.

    """
    selected_ids = tool_ids or get_default_tool_ids()
    tools: list[Tool[Any] | Callable[..., Any]] = []

    for tool_id in selected_ids:
        spec = TOOL_REGISTRY.get(tool_id)
        if not spec:
            continue

        tools.append(spec.tool)

    return tools
