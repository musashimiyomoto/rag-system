from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest import mock

import pytest

from ai.dependencies import Dependencies

if TYPE_CHECKING:
    from pydantic_ai import RunContext
from ai.tools.retrieve import retrieve


class _Source:
    def __init__(self, collection: str):
        self.collection = collection


@pytest.mark.asyncio
async def test_retrieve_uses_two_stage_ranking() -> None:
    deps = Dependencies(
        session=mock.AsyncMock(),
        source_ids=[10, 20],
        n_results=3,
        n_sources=2,
    )
    context = cast("RunContext[Dependencies]", SimpleNamespace(deps=deps))

    source_index_collection = mock.AsyncMock()
    source_index_collection.query.return_value = {
        "metadatas": [[{"source_id": 999}, {"source_id": 10}, {"source_id": 20}]],
    }

    source_collection_10 = mock.AsyncMock()
    source_collection_10.query.return_value = {
        "documents": [["doc-10-b", "doc-10-a"]],
        "distances": [[0.7, 0.2]],
    }
    source_collection_20 = mock.AsyncMock()
    source_collection_20.query.return_value = {
        "documents": [["doc-20-a", "doc-10-a"]],
        "distances": [[0.3, 0.4]],
    }

    chroma_client = mock.AsyncMock()
    chroma_client.get_or_create_collection.return_value = source_index_collection
    chroma_client.get_collection.side_effect = [
        source_collection_10,
        source_collection_20,
    ]

    with (
        mock.patch(
            "ai.tools.retrieve.chromadb.AsyncHttpClient",
            return_value=chroma_client,
        ),
        mock.patch(
            "ai.tools.retrieve.SourceRepository.get_by",
            side_effect=[_Source("collection-10"), _Source("collection-20")],
        ),
    ):
        result = await retrieve(context=context, search_query="test query")

    assert "[source:10] doc-10-a" in result
    assert "[source:20] doc-20-a" in result
    assert result.split("\n\n")[0] == "[source:10] doc-10-a"


@pytest.mark.asyncio
async def test_retrieve_returns_no_results_when_sources_not_selected() -> None:
    deps = Dependencies(
        session=mock.AsyncMock(),
        source_ids=[10],
        n_results=3,
        n_sources=2,
    )
    context = cast("RunContext[Dependencies]", SimpleNamespace(deps=deps))

    source_index_collection = mock.AsyncMock()
    source_index_collection.query.return_value = {
        "metadatas": [[{"source_id": 999}]],
    }

    chroma_client = mock.AsyncMock()
    chroma_client.get_or_create_collection.return_value = source_index_collection

    with mock.patch(
        "ai.tools.retrieve.chromadb.AsyncHttpClient",
        return_value=chroma_client,
    ):
        result = await retrieve(context=context, search_query="test query")

    assert result == "No data results found"
