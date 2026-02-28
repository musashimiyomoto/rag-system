import importlib
from email import message_from_bytes
from io import BytesIO
from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter
from prefect import flow, task
from pypdf import PdfReader

from ai.providers import list_provider_models
from ai.summarize import summarize
from ai.vector_store import ensure_collection, upsert_chunks
from constants import UTF8
from db.repositories import ProviderRepository, SourceFileRepository, SourceRepository
from db.sessions import async_session
from enums.source import SourceStatus, SourceType
from settings import BASE_PATH, core_settings, prefect_settings
from utils import decrypt


def _decode_text_content(content: bytes) -> str:
    """Decode text content.

    Args:
        content: The content parameter.

    Returns:
        Decoded text content.

    """
    return content.decode(encoding=UTF8, errors="ignore")


def _normalize_extracted_text(text: str) -> str:
    """Normalize extracted text.

    Args:
        text: The text parameter.

    Returns:
        Normalized text without empty lines.

    """
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _extract_html_text(raw_text: str) -> str:
    """Extract html text.

    Args:
        raw_text: The raw_text parameter.

    Returns:
        Plain text extracted from HTML.

    """
    beautiful_soup = importlib.import_module("bs4").BeautifulSoup

    return beautiful_soup(raw_text, features="html.parser").get_text(separator="\n")


def _extract_docx_text(content: bytes) -> str:
    """Extract docx text.

    Args:
        content: The content parameter.

    Returns:
        Plain text extracted from DOCX bytes.

    """
    document_class = importlib.import_module("docx").Document

    document = document_class(BytesIO(initial_bytes=content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _extract_rtf_text(content: bytes) -> str:
    """Extract rtf text.

    Args:
        content: The content parameter.

    Returns:
        Plain text extracted from RTF bytes.

    """
    rtf_to_text = importlib.import_module("striprtf.striprtf").rtf_to_text

    return rtf_to_text(_decode_text_content(content=content))


def _extract_odt_text(content: bytes) -> str:
    """Extract odt text.

    Args:
        content: The content parameter.

    Returns:
        Plain text extracted from ODT bytes.

    """
    teletype = importlib.import_module("odf.teletype")
    load = importlib.import_module("odf.opendocument").load
    paragraph_type = importlib.import_module("odf.text").P

    document = load(BytesIO(initial_bytes=content))
    return "\n".join(
        teletype.extractText(paragraph)
        for paragraph in document.getElementsByType(paragraph_type)
    )


def _extract_epub_text(content: bytes) -> str:
    """Extract epub text.

    Args:
        content: The content parameter.

    Returns:
        Plain text extracted from EPUB bytes.

    """
    beautiful_soup = importlib.import_module("bs4").BeautifulSoup
    ebooklib = importlib.import_module("ebooklib")
    epub = importlib.import_module("ebooklib.epub")

    book = epub.read_epub(name=BytesIO(initial_bytes=content))
    chunks = [
        beautiful_soup(item.get_content(), features="html.parser").get_text(
            separator="\n"
        )
        for item in book.get_items_of_type(item_type=ebooklib.ITEM_DOCUMENT)
    ]
    return "\n".join(chunks)


def _extract_pptx_text(content: bytes) -> str:
    """Extract pptx text.

    Args:
        content: The content parameter.

    Returns:
        Plain text extracted from PPTX bytes.

    """
    presentation_class = importlib.import_module("pptx").Presentation

    presentation = presentation_class(BytesIO(initial_bytes=content))
    chunks = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            text = getattr(shape, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def _extract_xlsx_text(content: bytes) -> str:
    """Extract xlsx text.

    Args:
        content: The content parameter.

    Returns:
        Plain text extracted from XLSX bytes.

    """
    load_workbook = importlib.import_module("openpyxl").load_workbook

    workbook = load_workbook(
        filename=BytesIO(initial_bytes=content), read_only=True, data_only=True
    )
    lines = []
    for worksheet in workbook.worksheets:
        lines.append(f"[{worksheet.title}]")
        for row in worksheet.iter_rows(values_only=True):
            values = [str(value) for value in row if value is not None]
            if values:
                lines.append("\t".join(values))
    return "\n".join(lines)


def _extract_eml_text(content: bytes) -> str:
    """Extract eml text.

    Args:
        content: The content parameter.

    Returns:
        Plain text extracted from EML bytes.

    """
    msg = message_from_bytes(content)
    chunks = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not isinstance(payload, bytes):
                continue

            if content_type == "text/plain":
                chunks.append(_decode_text_content(content=payload))
            elif content_type == "text/html":
                chunks.append(
                    _extract_html_text(raw_text=_decode_text_content(payload))
                )
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            content_type = msg.get_content_type()
            if content_type == "text/html":
                chunks.append(
                    _extract_html_text(raw_text=_decode_text_content(payload))
                )
            else:
                chunks.append(_decode_text_content(content=payload))

    return "\n".join(chunks)


async def deploy_process_source_flow(source_id: int) -> UUID:
    """Deploy the process source flow.

    Args:
        source_id: The source ID.

    Returns:
        The deployment ID.

    """
    deployment = await flow.from_source(
        source=BASE_PATH, entrypoint="flows/process_source.py:process_source"
    )  # ty:ignore[invalid-await]

    return await deployment.deploy(
        name=f"PROCESS_SOURCE_{source_id}",
        work_pool_name=prefect_settings.pool_name,
        parameters={"source_id": source_id},
        concurrency_limit=1,
        print_next_steps=False,
        ignore_warnings=True,
    )


async def get_or_create_collection(name: str) -> str:
    """Ensure Qdrant collection exists and return its name.

    Args:
        name: The collection name.

    Returns:
        The collection name.

    """
    await ensure_collection(name=name)
    return name


async def get_source_content(source_id: int) -> tuple[str, str, SourceType, bytes]:
    """Get source metadata and binary file content from PostgreSQL.

    Args:
        source_id: The source ID.

    Returns:
        A tuple containing collection name, source name, source type and binary
        content.

    Raises:
        ValueError: If source or source file is not found.

    """
    source_repository = SourceRepository()
    source_file_repository = SourceFileRepository()

    async with async_session() as session:
        source = await source_repository.update_by(
            session=session,
            id=source_id,
            data={"status": SourceStatus.PROCESSED},
        )
        if not source:
            msg = f"Source №{source_id} not found!"
            raise ValueError(msg)

        source_file = await source_file_repository.get_by(
            session=session, source_id=source_id
        )
        if not source_file:
            await source_repository.update_by(
                session=session,
                id=source_id,
                data={"status": SourceStatus.FAILED},
            )
            msg = f"For source №{source_id} not found file!"
            raise ValueError(msg)

    return source.collection, source.name, source.type, source_file.content


def _extract_text(source_type: SourceType, content: bytes) -> str:
    """Extract UTF-8 text from source bytes without writing to disk.

    Args:
        source_type: The source type.
        content: Raw file content.

    Returns:
        Extracted text.

    """
    if source_type in {SourceType.TXT, SourceType.MD}:
        text = _decode_text_content(content=content)
    elif source_type in {SourceType.HTML, SourceType.HTM}:
        text = _extract_html_text(raw_text=_decode_text_content(content=content))
    elif source_type == SourceType.PDF:
        text = "\n".join(
            page.extract_text() or ""
            for page in PdfReader(stream=BytesIO(initial_bytes=content)).pages
        )
    else:
        extractor = {
            SourceType.DOCX: _extract_docx_text,
            SourceType.RTF: _extract_rtf_text,
            SourceType.ODT: _extract_odt_text,
            SourceType.EPUB: _extract_epub_text,
            SourceType.PPTX: _extract_pptx_text,
            SourceType.XLSX: _extract_xlsx_text,
            SourceType.EML: _extract_eml_text,
        }.get(source_type)
        if not extractor:
            msg = f"Unsupported source type: {source_type.value}"
            raise ValueError(msg)
        text = extractor(content)

    return _normalize_extracted_text(text=text)


def _generate_chunks(text: str, chunk_size: int = 512) -> list[str]:
    """Generate chunks from extracted text.

    Args:
        text: The extracted text to split into chunks.
        chunk_size: The maximum size of each chunk.

    Returns:
        A list of text chunks.

    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=0
    ).split_text(text=text)


@task(name="Complete Processing Source")
async def _complete_processing_source(source_id: int, summary: str) -> None:
    """Complete source processing by updating status and summary.

    Args:
        source_id: The source ID.
        summary: The source summary.

    """
    repository = SourceRepository()

    async with async_session() as session:
        source = await repository.update_by(
            session=session,
            id=source_id,
            data={"status": SourceStatus.COMPLETED, "summary": summary},
        )
        if not source:
            msg = f"Source №{source_id} not found!"
            raise ValueError(msg)

    await upsert_chunks(
        collection=core_settings.sources_index_collection,
        ids=[f"source-{source.id}"],
        texts=[summary],
        payloads=[
            {
                "source_id": source.id,
                "source_name": source.name,
                "source_type": source.type.value,
            }
        ],
    )


@task(name="Index Source")
async def _index_source(source_id: int) -> list[str]:
    """Index the source by splitting it into chunks and storing in Qdrant.

    Args:
        source_id: The source ID.

    Returns:
        List of source chunks.

    """
    collection_name, source_name, source_type, content = await get_source_content(
        source_id=source_id
    )

    collection = await get_or_create_collection(name=collection_name)

    chunks = _generate_chunks(
        text=_extract_text(source_type=source_type, content=content)
    )

    await upsert_chunks(
        collection=collection,
        ids=[str(i) for i in range(len(chunks))],
        texts=chunks,
        payloads=[
            {
                "source_id": source_id,
                "source_name": source_name,
                "source_type": source_type.value,
                "chunk_id": i,
            }
            for i in range(len(chunks))
        ],
    )

    return chunks


@task(name="Summarize Source")
async def _summarize_source(source_id: int, chunks: list[str]) -> str:
    """Summarize the source by processing all chunks.

    Args:
        source_id: The source ID.
        chunks: The source chunks to summarize.

    Returns:
        The final source summary.

    """
    source_repository = SourceRepository()

    async with async_session() as session:
        provider = await ProviderRepository().get_by(session=session, is_active=True)
        if not provider or not provider.is_active:
            await source_repository.update_by(
                session=session, id=source_id, data={"status": SourceStatus.FAILED}
            )
            msg = "No active provider found!"
            raise ValueError(msg)

    models = list_provider_models(
        name=provider.name, api_key=decrypt(encrypted_data=provider.api_key_encrypted)
    )
    if len(models) > 0:
        model_name = models[0].name
    else:
        await source_repository.update_by(
            session=session, id=source_id, data={"status": SourceStatus.FAILED}
        )
        msg = f"No models found for provider {provider.name}!"
        raise ValueError(msg)

    return await summarize(
        texts=chunks,
        provider_name=provider.name,
        model_name=model_name,
        api_key_encrypted=provider.api_key_encrypted,
    )


@flow(name="Process Source", timeout_seconds=2 * 3600, retries=3)
async def process_source(source_id: int) -> None:
    """Process the source flow: index, summarize and complete processing.

    This flow handles the complete source processing pipeline:
    1. Index the source by splitting into chunks and storing in Qdrant
    2. Summarize the source content
    3. Mark the source as completed with the summary

    Args:
        source_id: The source ID to process.

    """
    chunks = await _index_source(source_id=source_id)

    summary = await _summarize_source(source_id=source_id, chunks=chunks)

    await _complete_processing_source(source_id=source_id, summary=summary)
