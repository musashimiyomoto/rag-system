import importlib
from email import message_from_bytes
from io import BytesIO

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from ai.vector_store import upsert_chunks
from constants import UTF8
from enums import SourceType


def _decode_text_content(content: bytes) -> str:
    """Decode text content.

    Args:
        content: Raw text bytes.

    Returns:
        Decoded text with invalid bytes ignored.

    """
    return content.decode(encoding=UTF8, errors="ignore")


def _normalize_extracted_text(text: str) -> str:
    """Normalize extracted text without empty lines.

    Args:
        text: Extracted text before normalization.

    Returns:
        Normalized text with trimmed non-empty lines.

    """
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _extract_html_text(raw_text: str) -> str:
    """Extract html text.

    Args:
        raw_text: Raw HTML content as text.

    Returns:
        Plain text extracted from HTML.

    """
    beautiful_soup = importlib.import_module("bs4").BeautifulSoup

    return beautiful_soup(raw_text, features="html.parser").get_text(separator="\n")


def _extract_docx_text(content: bytes) -> str:
    """Extract docx text.

    Args:
        content: DOCX file content bytes.

    Returns:
        Plain text extracted from DOCX paragraphs.

    """
    document_class = importlib.import_module("docx").Document

    document = document_class(BytesIO(initial_bytes=content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _extract_rtf_text(content: bytes) -> str:
    """Extract rtf text.

    Args:
        content: RTF file content bytes.

    Returns:
        Plain text extracted from RTF.

    """
    rtf_to_text = importlib.import_module("striprtf.striprtf").rtf_to_text

    return rtf_to_text(_decode_text_content(content=content))


def _extract_odt_text(content: bytes) -> str:
    """Extract odt text.

    Args:
        content: ODT file content bytes.

    Returns:
        Plain text extracted from ODT paragraphs.

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
        content: EPUB file content bytes.

    Returns:
        Plain text extracted from EPUB document items.

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
        content: PPTX file content bytes.

    Returns:
        Plain text extracted from slide shapes.

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
        content: XLSX file content bytes.

    Returns:
        Plain text representation of worksheet rows.

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
        content: EML file content bytes.

    Returns:
        Plain text extracted from supported email parts.

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


def _extract_text(source_type: SourceType, content: bytes) -> str:
    """Extract UTF-8 text from source bytes without writing to disk.

    Args:
        source_type: Source type describing extraction strategy.
        content: Source file content bytes.

    Returns:
        Normalized extracted text.

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
        text: Extracted source text.
        chunk_size: Maximum size of each chunk.

    Returns:
        List of text chunks ready for indexing.

    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=0
    ).split_text(text=text)


async def index_file_source(
    source_id: int,
    source_name: str,
    source_type: SourceType,
    collection: str,
    content: bytes,
) -> list[str]:
    """Index file source and return text chunks for summary.

    Args:
        source_id: Source ID to store in vector payload.
        source_name: Source name to store in vector payload.
        source_type: Source type used for text extraction.
        collection: Vector collection name.
        content: Source file content bytes.

    Returns:
        Text chunks used for indexing and summary generation.

    """
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
