from prefect import task

from ai.vector_store import ensure_collection
from enums import SourceType
from flows.db_processing.indexing import _index_db_source
from flows.file_processing.indexing import _index_file_source
from flows.source_loading import load_source_for_processing


@task(name="Index Source")
async def _index_source(source_id: int) -> list[str]:
    """Index source and route by source type."""
    source_data, file_content = await load_source_for_processing(source_id=source_id)

    collection = str(source_data["collection"])
    await ensure_collection(name=collection)

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
