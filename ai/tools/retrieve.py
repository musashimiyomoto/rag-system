from collections.abc import Mapping
from typing import Any

import chromadb
from chromadb.api.types import QueryResult
from pydantic_ai import RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import Dependencies
from db.repositories import SourceRepository
from settings import chroma_settings, core_settings


def _parse_source_id(metadata: Mapping[str, Any] | None) -> int | None:
    if not metadata:
        return None

    source_id_value = metadata.get("source_id")
    if isinstance(source_id_value, int):
        return source_id_value

    if isinstance(source_id_value, str) and source_id_value.isdigit():
        return int(source_id_value)

    return None


def _select_source_ids(
    source_level_results: QueryResult, allowed_source_ids: list[int], n_sources: int
) -> list[int]:
    metadatas = source_level_results.get("metadatas")
    if not metadatas or not metadatas[0]:
        return []

    selected_source_ids = []
    for metadata in metadatas[0]:
        source_id = _parse_source_id(metadata=metadata)
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
    source_repository = SourceRepository()
    ranked_chunks = []
    chroma_client = await chromadb.AsyncHttpClient(
        host=chroma_settings.host, port=chroma_settings.port
    )

    for source_id in selected_source_ids:
        source = await source_repository.get_by(session=session, id=source_id)
        if not source:
            continue

        source_collection = await chroma_client.get_collection(name=source.collection)
        source_results = await source_collection.query(
            query_texts=[search_query], n_results=n_results
        )
        documents = source_results.get("documents")
        if not documents or not documents[0]:
            continue

        distances = source_results.get("distances")
        scored_distances = distances[0] if distances and distances[0] else []
        for index, document in enumerate(documents[0]):
            distance = (
                float(scored_distances[index])
                if index < len(scored_distances)
                else float("inf")
            )
            ranked_chunks.append((distance, source_id, document))

    return ranked_chunks


def _format_ranked_chunks(
    ranked_chunks: list[tuple[float, int, str]],
    n_results: int,
) -> str:
    ranked_chunks.sort(key=lambda chunk: chunk[0])
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


async def retrieve(context: RunContext[Dependencies], search_query: str) -> str:
    """Retrieve text based on a search query.

    Args:
        context: The call context.
        search_query: The search query.

    """
    if len(context.deps.source_ids) == 0:
        return "No sources attached to this session"

    chroma_client = await chromadb.AsyncHttpClient(
        host=chroma_settings.host, port=chroma_settings.port
    )
    source_index = await chroma_client.get_or_create_collection(
        name=core_settings.sources_index_collection
    )
    source_level_results = await source_index.query(
        query_texts=[search_query],
        n_results=max(context.deps.n_sources * 4, context.deps.n_sources),
    )
    selected_source_ids = _select_source_ids(
        source_level_results=source_level_results,
        allowed_source_ids=context.deps.source_ids,
        n_sources=context.deps.n_sources,
    )
    if len(selected_source_ids) == 0:
        return "No data results found"

    ranked_chunks = await _collect_ranked_chunks(
        session=context.deps.session,
        search_query=search_query,
        selected_source_ids=selected_source_ids,
        n_results=context.deps.n_results,
    )
    if len(ranked_chunks) == 0:
        return "No data results found"

    return _format_ranked_chunks(
        ranked_chunks=ranked_chunks, n_results=context.deps.n_results
    )
