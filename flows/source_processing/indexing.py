import json
from collections.abc import AsyncIterator
from typing import Any

from prefect import task

from ai.vector_store import ensure_collection, upsert_chunks
from constants import (
    DB_SUMMARY_SAMPLE_LIMIT,
    DB_SUMMARY_TEXT_PREVIEW_LENGTH,
)
from db.connectors import (
    SourceDbConnectorError,
    stream_clickhouse_rows,
    stream_postgres_rows,
)
from db.models import SourceDb
from enums import SourceType
from flows.source_processing.extractors import _extract_text, _generate_chunks
from flows.source_processing.source_loading import load_source_for_processing
from utils import decrypt


async def get_or_create_collection(name: str) -> str:
    """Ensure Qdrant collection exists and return its name."""
    await ensure_collection(name=name)
    return name


def _normalize_payload_value(value: object) -> object:
    """Normalize payload value for Qdrant metadata."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        normalized = []
        for item in value:
            if isinstance(item, (str, int, float, bool)):
                normalized.append(item)
            else:
                normalized.append(str(item))
        return normalized

    return str(value)


def _select_db_row_stream(
    source_type: SourceType,
    credentials: dict[str, object],
    schema_name: str,
    table_name: str,
    columns: list[str],
) -> AsyncIterator[list[dict[str, Any]]]:
    """Select row stream implementation for DB source type."""
    if source_type == SourceType.POSTGRES:
        return stream_postgres_rows(
            credentials=credentials,
            schema_name=schema_name,
            table_name=table_name,
            columns=columns,
        )
    if source_type == SourceType.CLICKHOUSE:
        return stream_clickhouse_rows(
            credentials=credentials,
            schema_name=schema_name,
            table_name=table_name,
            columns=columns,
        )

    msg = f"Unsupported DB source type: {source_type.value}"
    raise ValueError(msg)


def _build_db_summary_header(source_name: str, source_db: SourceDb) -> str:
    """Build summary header for DB source."""
    filter_fields = (
        ", ".join(source_db.filter_fields) if source_db.filter_fields else "-"
    )
    return (
        f"Source {source_name}: table {source_db.schema_name}.{source_db.table_name}; "
        f"search_field={source_db.search_field}; "
        f"filter_fields={filter_fields}"
    )


def _prepare_db_point(
    source_id: int,
    source_name: str,
    source_type: SourceType,
    source_db: SourceDb,
    row: dict[str, object],
) -> tuple[str, str, dict[str, object], str] | None:
    """Prepare one DB row as Qdrant point payload."""
    row_id_value = row.get(source_db.id_field)
    if row_id_value is None:
        return None

    text = str(row.get(source_db.search_field) or "").strip()
    if len(text) == 0:
        return None

    row_id = str(row_id_value)
    payload: dict[str, object] = {
        "source_id": source_id,
        "source_name": source_name,
        "source_type": source_type.value,
        "source_backend": "db",
        "schema_name": source_db.schema_name,
        "table_name": source_db.table_name,
        "row_id": row_id,
    }
    for filter_field in source_db.filter_fields:
        payload[filter_field] = _normalize_payload_value(row.get(filter_field))

    point_id = f"db:{source_id}:{row_id}"
    return point_id, text, payload, row_id


async def _index_file_source(
    source_id: int,
    source_name: str,
    source_type: SourceType,
    collection: str,
    content: bytes,
) -> list[str]:
    """Index file source and return text chunks for summary."""
    chunks = _generate_chunks(
        text=_extract_text(source_type=source_type, content=content)
    )

    await upsert_chunks(
        collection=collection,
        ids=[f"file:{i}" for i in range(len(chunks))],
        texts=chunks,
        payloads=[
            {
                "source_id": source_id,
                "source_name": source_name,
                "source_type": source_type.value,
                "source_backend": "file",
                "chunk_id": i,
            }
            for i in range(len(chunks))
        ],
    )

    return chunks


async def _index_db_source(
    source_id: int,
    source_name: str,
    source_type: SourceType,
    collection: str,
    source_db: SourceDb | None,
) -> list[str]:
    """Index DB source table rows and return summary input chunks."""
    if source_db is None:
        msg = f"For source №{source_id} not found source_db!"
        raise ValueError(msg)

    credentials = json.loads(decrypt(encrypted_data=source_db.connection_encrypted))

    columns = list(
        dict.fromkeys(
            [source_db.id_field, source_db.search_field, *source_db.filter_fields]
        )
    )
    row_stream = _select_db_row_stream(
        source_type=source_type,
        credentials=credentials,
        schema_name=source_db.schema_name,
        table_name=source_db.table_name,
        columns=columns,
    )
    summary_chunks = [
        _build_db_summary_header(source_name=source_name, source_db=source_db)
    ]

    try:
        async for batch_rows in row_stream:
            ids = []
            texts = []
            payloads = []
            for row in batch_rows:
                point = _prepare_db_point(
                    source_id=source_id,
                    source_name=source_name,
                    source_type=source_type,
                    source_db=source_db,
                    row=row,
                )
                if point is None:
                    continue

                point_id, text, payload, row_id = point
                ids.append(point_id)
                texts.append(text)
                payloads.append(payload)

                if len(summary_chunks) < DB_SUMMARY_SAMPLE_LIMIT:
                    summary_chunks.append(
                        f"row {row_id}: {text[:DB_SUMMARY_TEXT_PREVIEW_LENGTH]}"
                    )

            if len(ids) > 0:
                await upsert_chunks(
                    collection=collection,
                    ids=ids,
                    texts=texts,
                    payloads=payloads,
                )
    except SourceDbConnectorError as exc:
        msg = f"Failed to stream DB source: {exc}"
        raise ValueError(msg) from exc

    return summary_chunks


@task(name="Index Source")
async def _index_source(source_id: int) -> list[str]:
    """Index source and return chunks for summary generation."""
    source_data, file_content = await load_source_for_processing(source_id=source_id)

    collection = await get_or_create_collection(name=str(source_data["collection"]))

    source_type = source_data["type"]

    if source_type in SourceType.get_db_types():
        return await _index_db_source(
            source_id=source_id,
            source_name=str(source_data["name"]),
            source_type=source_type,
            collection=collection,
            source_db=source_data["source_db"],
        )

    if file_content is None:
        msg = f"For source №{source_id} not found file content!"
        raise ValueError(msg)

    return await _index_file_source(
        source_id=source_id,
        source_name=str(source_data["name"]),
        source_type=source_type,
        collection=collection,
        content=file_content,
    )
