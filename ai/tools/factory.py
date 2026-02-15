from pydantic_ai import Tool
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

from ai.tools.retrieve import retrieve
from enums import ToolId

TOOL_REGISTRY: dict[ToolId, dict] = {
    ToolId.RETRIEVE: {
        "id": ToolId.RETRIEVE,
        "title": "Retrieve",
        "description": "Search through uploaded sources using vector similarity",
        "enabled_by_default": True,
        "requires_sources": True,
        "tool": Tool(retrieve),
    },
    ToolId.WEB_SEARCH: {
        "id": ToolId.WEB_SEARCH,
        "title": "Web Search",
        "description": "Search the web using DuckDuckGo",
        "enabled_by_default": True,
        "requires_sources": False,
        "tool": duckduckgo_search_tool(),
    },
}


def get_tools(tool_ids: list[ToolId]) -> list[Tool[None]]:
    tools: list[Tool[None]] = []
    for tool_id in tool_ids:
        tool = TOOL_REGISTRY.get(tool_id, {}).get("tool")

        if not tool:
            continue

        tools.append(tool)

    return tools
