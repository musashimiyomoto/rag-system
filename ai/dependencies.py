from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from constants import DEFAULT_N_RESULTS, DEFAULT_N_SOURCES


@dataclass
class RetrieveContext:
    n_results: int = DEFAULT_N_RESULTS
    n_sources: int = DEFAULT_N_SOURCES
    source_ids: list[int] | None = None


@dataclass
class AgentDeps:
    session: AsyncSession
    session_id: int
    session_source_ids: list[int]
    retrieve_context: RetrieveContext | None = None
