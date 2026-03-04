from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any
from uuid import uuid5

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from constants import EMBED_TIMEOUT, MAX_TEXT_LENGHT
from settings import ollama_settings, qdrant_settings


def _truncate_text(text: str) -> str:
    """Truncate one text string to max chars.

    Args:
        text: The text parameter.
    """
    if len(text) <= MAX_TEXT_LENGHT:
        return text

    return text[:MAX_TEXT_LENGHT]


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
                json={
                    "model": qdrant_settings.embedding_model,
                    "input": [_truncate_text(text=text) for text in texts],
                },
                timeout=EMBED_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            msg = "Failed to fetch embeddings from Ollama"
            raise ValueError(msg) from error

    if not isinstance(payload, dict):
        msg = "Invalid embeddings payload: expected dict"
        raise TypeError(msg)

    embeddings = payload.get("embeddings")

    if not isinstance(embeddings, list):
        msg = "Invalid embeddings payload: expected list[list[float]]"
        raise TypeError(msg)

    return embeddings


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
