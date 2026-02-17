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
    return str(uuid5(namespace=qdrant_settings.point_id_namespace, name=point_id))


def _resolve_distance() -> models.Distance:
    distance_map = {
        "COSINE": models.Distance.COSINE,
        "DOT": models.Distance.DOT,
        "EUCLID": models.Distance.EUCLID,
        "MANHATTAN": models.Distance.MANHATTAN,
    }
    return distance_map.get(qdrant_settings.distance.upper(), models.Distance.COSINE)


@lru_cache(maxsize=1)
def _get_embedder() -> TextEmbedding:
    if qdrant_settings.embedding_model:
        return TextEmbedding(model_name=qdrant_settings.embedding_model)

    return TextEmbedding()


@lru_cache(maxsize=1)
def _get_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(host=qdrant_settings.host, port=qdrant_settings.port)


def _embed_sync(texts: Sequence[str]) -> list[list[float]]:
    return [vector.tolist() for vector in _get_embedder().embed(documents=list(texts))]


async def _embed_texts(texts: Sequence[str]) -> list[list[float]]:
    return await asyncio.to_thread(_embed_sync, texts)


async def ensure_collection(name: str) -> None:
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
    if limit <= 0:
        return []

    client = _get_client()
    if not await client.collection_exists(collection_name=collection):
        return []

    return await client.search(
        collection_name=collection,
        query_vector=(await _embed_texts(texts=[query_text]))[0],
        query_filter=query_filter,
        with_payload=True,
        limit=limit,
    )


async def delete_collection(name: str) -> None:
    client = _get_client()
    if not await client.collection_exists(collection_name=name):
        return

    await client.delete_collection(collection_name=name)


async def delete_points(collection: str, ids: Sequence[str]) -> None:
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
    if _resolve_distance() in {models.Distance.EUCLID, models.Distance.MANHATTAN}:
        return -float(score)

    return float(score)
