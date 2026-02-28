from collections.abc import Mapping
from typing import Any

from pydantic_ai import RunContext
from qdrant_client.http import models
from qdrant_client.http.models import ScoredPoint
from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import AgentDeps
from ai.vector_store import relevance_score, search
from db.repositories import SourceDbRepository, SourceRepository
from settings import core_settings

MIN_RESULTS = 1
MAX_RESULTS = 20


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


def _normalize_n_results(requested: int | None, default: int) -> int:
    """Normalize n_results with safe bounds."""
    if requested is None:
        return default

    return min(max(int(requested), MIN_RESULTS), MAX_RESULTS)


def _build_query_filter(
    filters: Mapping[str, Any] | None,
    allowed_fields: set[str],
) -> models.Filter | None:
    """Build validated Qdrant filter for DB source."""
    if not filters:
        return None

    conditions = [
        _build_filter_condition(
            field_name=field_name,
            raw_spec=raw_spec,
            allowed_fields=allowed_fields,
        )
        for field_name, raw_spec in filters.items()
    ]

    if len(conditions) == 0:
        return None

    return models.Filter(must=conditions)


def _build_filter_condition(
    field_name: str,
    raw_spec: Any,
    allowed_fields: set[str],
) -> models.FieldCondition:
    """Build single validated filter condition."""
    if field_name not in allowed_fields:
        msg = f"Filter field '{field_name}' is not allowed"
        raise ValueError(msg)

    if not isinstance(raw_spec, dict):
        return models.FieldCondition(
            key=field_name,
            match=models.MatchValue(value=raw_spec),
        )

    if "eq" in raw_spec:
        return models.FieldCondition(
            key=field_name,
            match=models.MatchValue(value=raw_spec["eq"]),
        )

    if "in" in raw_spec:
        values = raw_spec["in"]
        if not isinstance(values, list) or len(values) == 0:
            msg = f"Filter '{field_name}.in' must be non-empty list"
            raise ValueError(msg)

        return models.FieldCondition(
            key=field_name,
            match=models.MatchAny(any=values),
        )

    range_value = raw_spec.get("range")
    if isinstance(range_value, dict):
        if not any(key in range_value for key in ["gt", "gte", "lt", "lte"]):
            msg = f"Filter '{field_name}.range' must contain gt/gte/lt/lte"
            raise ValueError(msg)

        return models.FieldCondition(
            key=field_name,
            range=models.Range(
                gt=range_value.get("gt"),
                gte=range_value.get("gte"),
                lt=range_value.get("lt"),
                lte=range_value.get("lte"),
            ),
        )

    msg = f"Unsupported filter operator for field '{field_name}'"
    raise ValueError(msg)


async def _collect_ranked_chunks(
    session: AsyncSession,
    search_query: str,
    selected_source_ids: list[int],
    n_results: int,
    filters: Mapping[str, Any] | None,
) -> list[tuple[float, int, str, str | None]]:
    """Collect ranked chunks.

    Args:
        session: The session parameter.
        search_query: The search_query parameter.
        selected_source_ids: The selected_source_ids parameter.
        n_results: The n_results parameter.
        filters: Optional metadata filters.

    Returns:
        Ranked chunks as (score, source_id, document, row_id) tuples.

    """
    source_repository = SourceRepository()
    source_db_repository = SourceDbRepository()
    ranked_chunks = []

    for source_id in selected_source_ids:
        source = await source_repository.get_by(session=session, id=source_id)
        if not source:
            continue

        query_filter: models.Filter | None = None
        source_db = await source_db_repository.get_by(
            session=session, source_id=source_id
        )
        if source_db and filters:
            query_filter = _build_query_filter(
                filters=filters,
                allowed_fields=set(source_db.filter_fields),
            )

        for point in await search(
            collection=source.collection,
            query_text=search_query,
            limit=n_results,
            query_filter=query_filter,
        ):
            payload = point.payload or {}
            document = payload.get("document")
            if not isinstance(document, str) or len(document.strip()) == 0:
                continue

            row_id = payload.get("row_id")
            ranked_chunks.append(
                (
                    relevance_score(score=point.score),
                    source_id,
                    document,
                    str(row_id) if row_id is not None else None,
                )
            )

    return ranked_chunks


def _format_ranked_chunks(
    ranked_chunks: list[tuple[float, int, str, str | None]],
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

    for _, source_id, document, row_id in ranked_chunks:
        if document in seen_documents:
            continue

        seen_documents.add(document)
        if row_id is None:
            deduplicated_results.append(f"[source:{source_id}] {document}")
        else:
            deduplicated_results.append(f"[source:{source_id} row:{row_id}] {document}")

        if len(deduplicated_results) >= n_results:
            break

    return "\n\n".join(deduplicated_results)


async def retrieve(
    context: RunContext[AgentDeps],
    search_query: str,
    filters: dict[str, Any] | None = None,
    n_results: int | None = None,
) -> str:
    """Retrieve text based on a search query.

    Args:
        context: The call context.
        search_query: The search query.
        filters: Optional metadata filters generated by the LLM.
        n_results: Optional result count override.

    Returns:
        The retrieved text or an error message.

    """
    retrieve_context = context.deps.retrieve_context
    if not retrieve_context:
        return "Retrieve tool is not configured for this run"

    allowed_source_ids = retrieve_context.source_ids or context.deps.session_source_ids
    if len(allowed_source_ids) == 0:
        return "No sources attached to this session"

    effective_n_results = _normalize_n_results(
        requested=n_results, default=retrieve_context.n_results
    )

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

    try:
        ranked_chunks = await _collect_ranked_chunks(
            session=context.deps.session,
            search_query=search_query,
            selected_source_ids=selected_source_ids,
            n_results=effective_n_results,
            filters=filters,
        )
    except ValueError as exc:
        return f"Invalid retrieve filters: {exc}"

    if len(ranked_chunks) == 0:
        return "No data results found"

    return _format_ranked_chunks(
        ranked_chunks=ranked_chunks, n_results=effective_n_results
    )
