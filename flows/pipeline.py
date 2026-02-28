from prefect import flow

from flows.completion import _complete_processing_source
from flows.indexing import _index_source
from flows.summarization import _summarize_source


@flow(name="Process Source", timeout_seconds=2 * 3600, retries=3)
async def process_source(source_id: int) -> None:
    """Process the source flow: index, summarize and complete processing."""
    chunks = await _index_source(source_id=source_id)

    summary = await _summarize_source(source_id=source_id, chunks=chunks)

    await _complete_processing_source(source_id=source_id, summary=summary)
