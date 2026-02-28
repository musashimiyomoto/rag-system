from ai.vector_store import upsert_chunks
from enums import SourceType
from flows.file_processing.extractors import (
    _extract_text,
    _generate_chunks,
)


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
