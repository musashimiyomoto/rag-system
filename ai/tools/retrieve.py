import chromadb
from pydantic_ai import RunContext

from ai.dependencies import Dependencies
from db.repositories import SourceRepository
from settings import chroma_settings


async def retrieve(context: RunContext[Dependencies], search_query: str) -> str:
    """Retrieve text based on a search query.

    Args:
        context: The call context.
        search_query: The search query.

    """
    chroma_client = await chromadb.AsyncHttpClient(
        host=chroma_settings.host,
        port=chroma_settings.port,
    )

    source = await SourceRepository().get_by(
        session=context.deps.session, id=context.deps.source_id
    )
    if not source:
        return "Source not found"

    source_collection = await chroma_client.get_collection(
        name=source.collection,
    )

    source_results = await source_collection.query(
        query_texts=[search_query],
        n_results=context.deps.n_results,
    )
    documents = source_results.get("documents")
    if not documents:
        return "No data results found"

    return "\n\n".join(documents[0])
