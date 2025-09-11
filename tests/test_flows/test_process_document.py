from typing import AsyncGenerator
from unittest import mock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from enums import DocumentStatus
from flows.process_document import (
    _complete_processing_document,
    _index_document,
    _summarize_document,
)
from tests.base import BaseTestCase
from tests.factories import DocumentFactory


class TestIndexDocumentTask(BaseTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def _mock_redis(self) -> AsyncGenerator[mock.MagicMock, None]:
        async def mock_get(name: str) -> str:
            return "bW9ja2Jhc2U2NGNvbnRlbnQ="

        with mock.patch("flows.process_document.redis_client") as mock_redis:
            mock_redis.get.side_effect = mock_get
            mock_redis.delete.return_value = None
            yield mock_redis

    @pytest_asyncio.fixture(autouse=True)
    async def _mock_chromadb(self) -> AsyncGenerator[mock.MagicMock, None]:
        mock_collection = mock.AsyncMock()
        mock_collection.add.return_value = None

        async def mock_get_or_create_collection(name: str):
            return mock_collection

        with mock.patch(
            "flows.process_document.get_or_create_collection",
            side_effect=mock_get_or_create_collection,
        ):
            yield mock_collection

    @pytest_asyncio.fixture(autouse=True)
    async def _mock_textract(self) -> AsyncGenerator[mock.MagicMock, None]:
        with mock.patch("flows.process_document.textract.process") as mock_textract:
            mock_textract.return_value = b"Sample document content for testing purposes"
            yield mock_textract

    @pytest.mark.asyncio
    async def test_success(self, test_session: AsyncSession):
        document = await DocumentFactory.create_async(session=self.session)
        mock_context_manager = mock.AsyncMock()
        mock_context_manager.__aenter__.return_value = test_session
        mock_context_manager.__aexit__.return_value = None
        mock_async_session = mock.Mock(return_value=mock_context_manager)

        with mock.patch("flows.process_document.async_session", mock_async_session):
            chunks = await _index_document.fn(document_id=document.id)

            assert isinstance(chunks, list)
            assert len(chunks) > 0
            assert all(isinstance(chunk, str) for chunk in chunks)


class TestSummarizeDocumentTask(BaseTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def _mock_summarize(self) -> AsyncGenerator[mock.MagicMock, None]:
        with mock.patch("flows.process_document.summarize") as mock_summarize:
            mock_summarize.return_value = "Mocked summary for chunk"
            yield mock_summarize

    @pytest.mark.asyncio
    async def test_success(self):
        test_chunks = [
            "This is the first chunk of the document.",
            "This is the second chunk of the document.",
            "This is the third chunk of the document.",
        ]

        summary = await _summarize_document.fn(chunks=test_chunks)

        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Mocked summary for chunk" in summary


class TestCompleteProcessingDocumentTask(BaseTestCase):
    @pytest.mark.asyncio
    async def test_success(self, test_session: AsyncSession):
        document = await DocumentFactory.create_async(session=self.session)
        test_summary = "This is a test summary for the document"

        mock_context_manager = mock.AsyncMock()
        mock_context_manager.__aenter__.return_value = test_session
        mock_context_manager.__aexit__.return_value = None
        mock_async_session = mock.Mock(return_value=mock_context_manager)

        with mock.patch("flows.process_document.async_session", mock_async_session):
            await _complete_processing_document.fn(
                document_id=document.id, summary=test_summary
            )

            await self.session.refresh(document)
            assert document.status == DocumentStatus.COMPLETED
            assert document.summary == test_summary
