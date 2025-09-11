import chromadb
from pydantic_ai import RunContext

from ai.dependencies import Dependencies
from db.repositories import DocumentRepository
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

    document = await DocumentRepository().get_by(
        session=context.deps.session, id=context.deps.document_id
    )
    if not document:
        return "Document not found"

    document_collection = await chroma_client.get_collection(
        name=document.collection,
    )

    document_results = await document_collection.query(
        query_texts=[search_query],
        n_results=context.deps.n_results,
    )
    documents = document_results.get("documents")
    if not documents:
        return "No data results found"

    return "\n\n".join(documents[0])
