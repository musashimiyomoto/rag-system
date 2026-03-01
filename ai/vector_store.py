import asyncio
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any
from uuid import uuid5

from fastembed import TextEmbedding
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from settings import qdrant_settings


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
def _get_embedder() -> TextEmbedding:
    """Get embedder.

    Returns:
        The embedder.

    """
    return TextEmbedding()


@lru_cache(maxsize=1)
def _get_client() -> AsyncQdrantClient:
    """Get client.

    Returns:
        Configured async Qdrant client.

    """
    return AsyncQdrantClient(host=qdrant_settings.host, port=qdrant_settings.port)


def _embed_sync(texts: Sequence[str]) -> list[list[float]]:
    """Embed sync.

    Args:
        texts: The texts parameter.

    Returns:
        Vector embeddings.

    """
    return [vector.tolist() for vector in _get_embedder().embed(documents=list(texts))]


async def _embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed texts.

    Args:
        texts: The texts parameter.

    Returns:
        Vector embeddings.

    """
    return await asyncio.to_thread(_embed_sync, texts)


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
