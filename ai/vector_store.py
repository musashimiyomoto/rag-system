from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any
from uuid import uuid5

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from constants import EMBED_TIMEOUT
from settings import ollama_settings, qdrant_settings


def _normalize_point_id(point_id: str) -> str:
    """Normalize point id.

    Args:
        point_id: The point_id parameter.

    Returns:
        Normalized point id.

    """
    return str(
        object=uuid5(namespace=qdrant_settings.point_id_namespace, name=point_id)
    )


def _resolve_distance() -> models.Distance:
    """Resolve distance.

    Returns:
        Distance.

    """
    distance_map = {
        "COSINE": models.Distance.COSINE,
        "DOT": models.Distance.DOT,
        "EUCLID": models.Distance.EUCLID,
        "MANHATTAN": models.Distance.MANHATTAN,
    }
    return distance_map.get(qdrant_settings.distance.upper(), models.Distance.COSINE)


@lru_cache(maxsize=1)
def _get_client() -> AsyncQdrantClient:
    """Get client.

    Returns:
        Configured async Qdrant client.

    """
    return AsyncQdrantClient(host=qdrant_settings.host, port=qdrant_settings.port)


def _validate_vector(vector: Any, *, index: int) -> list[float]:
    """Validate and normalize one embedding vector.

    Args:
        vector: Raw embedding vector payload.
        index: Index of the vector in the response payload.

    Returns:
        Normalized embedding vector.

    Raises:
        TypeError: If the vector format is invalid.
        ValueError: If vector dimension is invalid.

    """
    if not isinstance(vector, list):
        msg = f"Invalid embedding at index {index}: expected list[float]"
        raise TypeError(msg)

    normalized = []
    for value in vector:
        if not isinstance(value, int | float):
            msg = f"Invalid embedding value at index {index}: expected numeric value"
            raise TypeError(msg)
        normalized.append(float(value))

    actual_size = len(normalized)
    expected_size = qdrant_settings.vector_size
    if actual_size != expected_size:
        model = qdrant_settings.embedding_model
        msg = (
            f"Embedding dimension mismatch for model '{model}': "
            f"expected {expected_size}, got {actual_size}"
        )
        raise ValueError(msg)

    return normalized


def _validate_embeddings(embeddings: Any, *, expected_count: int) -> list[list[float]]:
    """Validate and normalize embedding response payload.

    Args:
        embeddings: Raw embeddings payload.
        expected_count: Number of vectors expected in response.

    Returns:
        Normalized embeddings.

    Raises:
        TypeError: If payload shape/content types are invalid.
        ValueError: If embeddings count is invalid.

    """
    if not isinstance(embeddings, list):
        msg = "Invalid embeddings payload: expected list[list[float]]"
        raise TypeError(msg)

    if len(embeddings) != expected_count:
        msg = (
            f"Invalid embeddings count: expected {expected_count}, "
            f"got {len(embeddings)}"
        )
        raise ValueError(msg)

    return [
        _validate_vector(vector=vector, index=index)
        for index, vector in enumerate(embeddings)
    ]


async def _embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed texts via Ollama.

    Args:
        texts: The texts parameter.

    Returns:
        Vector embeddings.

    Raises:
        ValueError: If embedding request or payload validation fails.

    """
    if len(texts) == 0:
        return []

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url=f"{ollama_settings.url}/api/embed",
                json={"model": qdrant_settings.embedding_model, "input": texts},
                timeout=EMBED_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            msg = "Failed to fetch embeddings from Ollama"
            raise ValueError(msg) from error

    return _validate_embeddings(
        embeddings=payload.get("embeddings") if isinstance(payload, dict) else None,
        expected_count=len(texts),
    )


async def ensure_collection(name: str) -> None:
    """Ensure collection.

    Args:
        name: The name parameter.

    """
    client = _get_client()
    if await client.collection_exists(collection_name=name):
        return

    await client.create_collection(
        collection_name=name,
        vectors_config=models.VectorParams(
            size=qdrant_settings.vector_size,
            distance=_resolve_distance(),
        ),
    )


async def upsert_chunks(
    collection: str,
    ids: Sequence[str],
    texts: Sequence[str],
    payloads: Sequence[Mapping[str, Any] | None],
) -> None:
    """Upsert chunks.

    Args:
        collection: The collection parameter.
        ids: The ids parameter.
        texts: The texts parameter.
        payloads: The payloads parameter.

    """
    if len(ids) != len(texts) or len(ids) != len(payloads):
        msg = "ids, texts and payloads must have the same length"
        raise ValueError(msg)

    if len(ids) == 0:
        return

    await ensure_collection(name=collection)

    vectors = await _embed_texts(texts=texts)
    points = [
        models.PointStruct(
            id=_normalize_point_id(point_id),
            vector=vector,
            payload={"document": text, **(dict(payload or {}))},
        )
        for point_id, vector, text, payload in zip(
            ids, vectors, texts, payloads, strict=True
        )
    ]

    await _get_client().upsert(collection_name=collection, points=points, wait=True)


async def search(
    collection: str,
    query_text: str,
    limit: int,
    query_filter: models.Filter | None = None,
) -> list[models.ScoredPoint]:
    """Search.

    Args:
        collection: The collection parameter.
        query_text: The query_text parameter.
        limit: The limit parameter.
        query_filter: The query_filter parameter.

    Returns:
        Scored points matching the query.

    """
    if limit <= 0:
        return []

    client = _get_client()
    if not await client.collection_exists(collection_name=collection):
        return []

    result = await client.query_points(
        collection_name=collection,
        query=(await _embed_texts(texts=[query_text]))[0],
        query_filter=query_filter,
        with_payload=True,
        limit=limit,
    )

    return result.points


async def delete_collection(name: str) -> None:
    """Delete collection.

    Args:
        name: The name parameter.

    """
    client = _get_client()
    if not await client.collection_exists(collection_name=name):
        return

    await client.delete_collection(collection_name=name)


async def delete_points(collection: str, ids: Sequence[str]) -> None:
    """Delete points.

    Args:
        collection: The collection parameter.
        ids: The ids parameter.

    """
    if len(ids) == 0:
        return

    client = _get_client()
    if not await client.collection_exists(collection_name=collection):
        return

    await client.delete(
        collection_name=collection,
        points_selector=models.PointIdsList(
            points=[_normalize_point_id(point_id) for point_id in ids]
        ),
        wait=True,
    )


def relevance_score(score: float) -> float:
    """Relevance score.

    Args:
        score: The score parameter.

    Returns:
        Relevance score.

    """
    if _resolve_distance() in {models.Distance.EUCLID, models.Distance.MANHATTAN}:
        return -float(score)

    return float(score)
