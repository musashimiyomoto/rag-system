from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from ai.dependencies import AgentDeps, ToolContext
from ai.tools.retrieve import retrieve

if TYPE_CHECKING:
    from pydantic_ai import RunContext


@pytest.mark.asyncio
async def test_retrieve_returns_not_configured_without_context(test_session) -> None:
    deps = AgentDeps(
        session=test_session,
        session_id=1,
        source_ids=[],
        tool_context=ToolContext(retrieve=None, web_search=None),
    )

    context = cast("RunContext[AgentDeps]", SimpleNamespace(deps=deps))
    result = await retrieve(context=context, search_query="test")

    assert result == "Retrieve tool is not configured for this run"
