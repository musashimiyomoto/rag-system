from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from constants import DEFAULT_N_RESULTS, DEFAULT_N_SOURCES


@dataclass
class RetrieveContext:
    n_results: int = DEFAULT_N_RESULTS
    n_sources: int = DEFAULT_N_SOURCES
    allowed_source_ids: list[int] | None = None


@dataclass
class WebSearchContext:
    enabled: bool = True


@dataclass
class ToolContext:
    retrieve: RetrieveContext | None = None
    web_search: WebSearchContext | None = None


@dataclass
class AgentDeps:
    session: AsyncSession
    session_id: int
    source_ids: list[int]
    tool_context: ToolContext
