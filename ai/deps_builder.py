from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import AgentDeps, RetrieveContext, ToolContext, WebSearchContext
from ai.tools import get_default_tool_ids
from db.repositories import SessionSourceRepository
from enums import ToolId


async def _get_source_ids(session: AsyncSession, session_id: int) -> list[int]:
    session_sources = await SessionSourceRepository().get_all(
        session=session, session_id=session_id
    )
    return [session_source.source_id for session_source in session_sources]


async def build_agent_deps(
    session: AsyncSession, session_id: int, tool_ids: list[ToolId]
) -> AgentDeps:
    effective_tool_ids = tool_ids or get_default_tool_ids()
    source_ids = await _get_source_ids(session=session, session_id=session_id)

    retrieve_context = (
        RetrieveContext(allowed_source_ids=source_ids)
        if ToolId.RETRIEVE in effective_tool_ids
        else None
    )
    web_search_context = (
        WebSearchContext() if ToolId.WEB_SEARCH in effective_tool_ids else None
    )

    return AgentDeps(
        session=session,
        session_id=session_id,
        source_ids=source_ids,
        tool_context=ToolContext(
            retrieve=retrieve_context, web_search=web_search_context
        ),
    )
