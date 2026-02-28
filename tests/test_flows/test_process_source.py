from typing import AsyncGenerator
from unittest import mock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from enums import SourceStatus, SourceType
from flows.completion import _complete_processing_source
from flows.file_processing.extractors import _extract_text
from flows.indexing import _index_source
from flows.summarization import _summarize_source
from tests.base import BaseTestCase
from tests.factories import (
    ProviderFactory,
    SourceDbFactory,
    SourceFactory,
    SourceFileFactory,
)
from utils import encrypt

MIN_EXPECTED_DB_SUMMARY_CHUNKS = 2


class TestIndexSourceTask(BaseTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def _mock_vector_store(self) -> AsyncGenerator[mock.MagicMock, None]:
        with (
            mock.patch("flows.indexing.ensure_collection") as mock_ensure_collection,
            mock.patch(
                "flows.file_processing.indexing.upsert_chunks"
            ) as mock_upsert_chunks,
            mock.patch(
                "flows.db_processing.indexing.upsert_chunks"
            ) as mock_upsert_chunks_db,
        ):
            mock_ensure_collection.return_value = None
            mock_upsert_chunks.return_value = None
            mock_upsert_chunks_db.return_value = None
            yield mock_upsert_chunks

    @pytest.mark.asyncio
    async def test_success(self, test_session: AsyncSession):
        source = await SourceFactory.create_async(
            session=self.session, type=SourceType.TXT
        )
        await SourceFileFactory.create_async(
            session=self.session,
            source_id=source.id,
            content=b"Sample source content for testing purposes",
        )
        mock_context_manager = mock.AsyncMock()
        mock_context_manager.__aenter__.return_value = test_session
        mock_context_manager.__aexit__.return_value = None
        mock_async_session = mock.Mock(return_value=mock_context_manager)

        with mock.patch("flows.source_loading.async_session", mock_async_session):
            chunks = await _index_source.fn(source_id=source.id)

            assert isinstance(chunks, list)
            assert len(chunks) > 0
            assert all(isinstance(chunk, str) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_missing_source_file_marks_failed(self, test_session: AsyncSession):
        source = await SourceFactory.create_async(session=self.session)
        mock_context_manager = mock.AsyncMock()
        mock_context_manager.__aenter__.return_value = test_session
        mock_context_manager.__aexit__.return_value = None
        mock_async_session = mock.Mock(return_value=mock_context_manager)

        with (
            mock.patch(
                "flows.source_loading.async_session",
                mock_async_session,
            ),
            pytest.raises(ValueError, match="not found file"),
        ):
            await _index_source.fn(source_id=source.id)

        await self.session.refresh(source)
        assert source.status == SourceStatus.FAILED

    @pytest.mark.asyncio
    async def test_db_source_success(self, test_session: AsyncSession):
        source = await SourceFactory.create_async(
            session=self.session, type=SourceType.POSTGRES
        )
        await SourceDbFactory.create_async(
            session=self.session,
            source_id=source.id,
            db_type=SourceType.POSTGRES,
            connection_encrypted=encrypt(
                '{"host":"localhost","port":5432,"database":"db","user":"u","password":"p"}'
            ),
            schema_name="public",
            table_name="products",
            id_field="id",
            search_field="content",
            filter_fields=["category"],
        )
        mock_context_manager = mock.AsyncMock()
        mock_context_manager.__aenter__.return_value = test_session
        mock_context_manager.__aexit__.return_value = None
        mock_async_session = mock.Mock(return_value=mock_context_manager)

        async def stream_rows(*args, **kwargs):
            yield [
                {"id": 1, "content": "Product 1", "category": "books"},
                {"id": 2, "content": "Product 2", "category": "games"},
            ]

        with (
            mock.patch(
                "flows.source_loading.async_session",
                mock_async_session,
            ),
            mock.patch(
                "flows.db_processing.indexing.stream_postgres_rows",
                side_effect=stream_rows,
            ),
        ):
            chunks = await _index_source.fn(source_id=source.id)

        assert isinstance(chunks, list)
        assert len(chunks) >= MIN_EXPECTED_DB_SUMMARY_CHUNKS
        assert any("row 1: Product 1" in item for item in chunks)


class TestExtractText(BaseTestCase):
    @pytest.mark.asyncio
    async def test_txt(self):
        text = _extract_text(
            source_type=SourceType.TXT,
            content=b"Simple text content",
        )
        assert text == "Simple text content"

    @pytest.mark.asyncio
    async def test_pdf(self):
        page_1 = mock.Mock()
        page_1.extract_text.return_value = "First page"
        page_2 = mock.Mock()
        page_2.extract_text.return_value = "Second page"
        mocked_reader = mock.Mock()
        mocked_reader.pages = [page_1, page_2]

        with mock.patch(
            "flows.file_processing.extractors.PdfReader",
            return_value=mocked_reader,
        ):
            text = _extract_text(source_type=SourceType.PDF, content=b"%PDF")

        assert text == "First page\nSecond page"

    @pytest.mark.asyncio
    async def test_md(self):
        text = _extract_text(
            source_type=SourceType.MD,
            content=b"# Header\n\nBody",
        )
        assert text == "# Header\nBody"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("source_type", [SourceType.HTML, SourceType.HTM])
    async def test_html(self, source_type: SourceType):
        with mock.patch(
            "flows.file_processing.extractors._extract_html_text",
            return_value="Title\n\nBody",
        ):
            text = _extract_text(source_type=source_type, content=b"<html></html>")
        assert text == "Title\nBody"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("source_type", "helper_name"),
        [
            (SourceType.DOCX, "_extract_docx_text"),
            (SourceType.RTF, "_extract_rtf_text"),
            (SourceType.ODT, "_extract_odt_text"),
            (SourceType.EPUB, "_extract_epub_text"),
            (SourceType.PPTX, "_extract_pptx_text"),
            (SourceType.XLSX, "_extract_xlsx_text"),
            (SourceType.EML, "_extract_eml_text"),
        ],
    )
    async def test_supported_binary_types(
        self, source_type: SourceType, helper_name: str
    ):
        with mock.patch(
            f"flows.file_processing.extractors.{helper_name}",
            return_value="A\n\nB",
        ):
            text = _extract_text(source_type=source_type, content=b"binary")
        assert text == "A\nB"


class TestSummarizeSourceTask(BaseTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def _mock_summarize(self) -> AsyncGenerator[mock.MagicMock, None]:
        with mock.patch("flows.summarization.summarize") as mock_summarize:
            mock_summarize.return_value = "Mocked summary for chunk"
            yield mock_summarize

    @pytest.mark.asyncio
    async def test_success(self, test_session: AsyncSession):
        await ProviderFactory.create_async(session=self.session)

        test_chunks = [
            "This is the first chunk of the source.",
            "This is the second chunk of the source.",
            "This is the third chunk of the source.",
        ]

        mock_model = mock.Mock()
        mock_model.name = "test_model"

        mock_context_manager = mock.AsyncMock()
        mock_context_manager.__aenter__.return_value = test_session
        mock_context_manager.__aexit__.return_value = None
        mock_async_session = mock.Mock(return_value=mock_context_manager)

        with (
            mock.patch(
                "flows.summarization.async_session",
                mock_async_session,
            ),
            mock.patch(
                "flows.summarization.list_provider_models",
                return_value=[mock_model],
            ),
            mock.patch(
                "flows.summarization.decrypt",
                return_value="decrypted_key",
            ),
        ):
            summary = await _summarize_source.fn(source_id=1, chunks=test_chunks)

            assert isinstance(summary, str)
            assert len(summary) > 0
            assert "Mocked summary for chunk" in summary


class TestCompleteProcessingSourceTask(BaseTestCase):
    @pytest.mark.asyncio
    async def test_success(self, test_session: AsyncSession):
        source = await SourceFactory.create_async(session=self.session)
        test_summary = "This is a test summary for the source"

        mock_context_manager = mock.AsyncMock()
        mock_context_manager.__aenter__.return_value = test_session
        mock_context_manager.__aexit__.return_value = None
        mock_async_session = mock.Mock(return_value=mock_context_manager)

        with (
            mock.patch(
                "flows.completion.async_session",
                mock_async_session,
            ),
            mock.patch("flows.completion.upsert_chunks") as mock_upsert_chunks,
        ):
            await _complete_processing_source.fn(
                source_id=source.id, summary=test_summary
            )

            await self.session.refresh(source)
            assert source.status == SourceStatus.COMPLETED
            assert source.summary == test_summary
            mock_upsert_chunks.assert_awaited_once()
