from ai.tools.factory import TOOL_REGISTRY, get_default_tool_ids, get_tools
from enums import ToolId


def test_get_tools_returns_ordered_tools() -> None:
    tool_ids = [ToolId.WEB_SEARCH, ToolId.RETRIEVE]

    tools = get_tools(tool_ids=tool_ids)

    assert tools == [
        TOOL_REGISTRY[ToolId.WEB_SEARCH].tool,
        TOOL_REGISTRY[ToolId.RETRIEVE].tool,
    ]


def test_get_tools_uses_default_when_empty() -> None:
    default_ids = get_default_tool_ids()

    tools = get_tools(tool_ids=[])

    assert tools == [TOOL_REGISTRY[tool_id].tool for tool_id in default_ids]
