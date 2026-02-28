from collections.abc import Mapping
from typing import Any

from pydantic_ai import RunContext
from qdrant_client.http.models import ScoredPoint
from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import AgentDeps
from ai.vector_store import relevance_score, search
from db.repositories import SourceRepository
from settings import core_settings


def _parse_source_id(payload: Mapping[str, Any] | None) -> int | None:
    """Parse source id.

    Args:
        payload: The payload parameter.

    Returns:
        Parsed source ID or None when unavailable.

    """
    if not payload:
        return None

    source_id_value = payload.get("source_id")
    if isinstance(source_id_value, int):
        return source_id_value

    if isinstance(source_id_value, str) and source_id_value.isdigit():
        return int(source_id_value)

    return None


def _select_source_ids(
    source_level_results: list[ScoredPoint],
    allowed_source_ids: list[int],
    n_sources: int,
) -> list[int]:
    """Select source ids.

    Args:
        source_level_results: The source_level_results parameter.
        allowed_source_ids: The allowed_source_ids parameter.
        n_sources: The n_sources parameter.

    Returns:
        Source IDs selected for chunk retrieval.

    """
    selected_source_ids = []

    for point in source_level_results:
        source_id = _parse_source_id(payload=point.payload)
        if (
            source_id is None
            or source_id not in allowed_source_ids
            or source_id in selected_source_ids
        ):
            continue

        selected_source_ids.append(source_id)
        if len(selected_source_ids) >= n_sources:
            break

    return selected_source_ids


async def _collect_ranked_chunks(
    session: AsyncSession,
    search_query: str,
    selected_source_ids: list[int],
    n_results: int,
) -> list[tuple[float, int, str]]:
    """Collect ranked chunks.

    Args:
        session: The session parameter.
        search_query: The search_query parameter.
        selected_source_ids: The selected_source_ids parameter.
        n_results: The n_results parameter.

    Returns:
        Ranked chunks as (score, source_id, document) tuples.

    """
    source_repository = SourceRepository()
    ranked_chunks = []

    for source_id in selected_source_ids:
        source = await source_repository.get_by(session=session, id=source_id)
        if not source:
            continue

        for point in await search(
            collection=source.collection, query_text=search_query, limit=n_results
        ):
            payload = point.payload or {}
            document = payload.get("document")
            if not isinstance(document, str) or len(document.strip()) == 0:
                continue

            ranked_chunks.append(
                (relevance_score(score=point.score), source_id, document)
            )

    return ranked_chunks


def _format_ranked_chunks(
    ranked_chunks: list[tuple[float, int, str]],
    n_results: int,
) -> str:
    """Format ranked chunks.

    Args:
        ranked_chunks: The ranked_chunks parameter.
        n_results: The n_results parameter.

    Returns:
        Formatted deduplicated chunks for the agent response.

    """
    ranked_chunks.sort(key=lambda chunk: chunk[0], reverse=True)
    deduplicated_results = []
    seen_documents = set()

    for _, source_id, document in ranked_chunks:
        if document in seen_documents:
            continue

        seen_documents.add(document)
        deduplicated_results.append(f"[source:{source_id}] {document}")
        if len(deduplicated_results) >= n_results:
            break

    return "\n\n".join(deduplicated_results)


async def retrieve(context: RunContext[AgentDeps], search_query: str) -> str:
    """Retrieve text based on a search query.

    Args:
        context: The call context.
        search_query: The search query.

    Returns:
        The retrieved text or an error message.

    """
    retrieve_context = context.deps.tool_context.retrieve
    if not retrieve_context:
        return "Retrieve tool is not configured for this run"

    allowed_source_ids = retrieve_context.allowed_source_ids or context.deps.source_ids
    if len(allowed_source_ids) == 0:
        return "No sources attached to this session"

    source_level_results = await search(
        collection=core_settings.sources_index_collection,
        query_text=search_query,
        limit=max(retrieve_context.n_sources * 4, retrieve_context.n_sources),
    )
    selected_source_ids = _select_source_ids(
        source_level_results=source_level_results,
        allowed_source_ids=allowed_source_ids,
        n_sources=retrieve_context.n_sources,
    )
    if len(selected_source_ids) == 0:
        return "No data results found"

    ranked_chunks = await _collect_ranked_chunks(
        session=context.deps.session,
        search_query=search_query,
        selected_source_ids=selected_source_ids,
        n_results=retrieve_context.n_results,
    )
    if len(ranked_chunks) == 0:
        return "No data results found"

    return _format_ranked_chunks(
        ranked_chunks=ranked_chunks, n_results=retrieve_context.n_results
    )
