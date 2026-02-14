from typing import AsyncGenerator
from unittest import mock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from enums import SourceStatus
from flows.process_source import (
    _complete_processing_source,
    _index_source,
    _summarize_source,
)
from tests.base import BaseTestCase
from tests.factories import SourceFactory


class TestIndexSourceTask(BaseTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def _mock_redis(self) -> AsyncGenerator[mock.MagicMock, None]:
        async def mock_get(name: str) -> str:
            return "bW9ja2Jhc2U2NGNvbnRlbnQ="

        with mock.patch("flows.process_source.redis_client") as mock_redis:
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
            "flows.process_source.get_or_create_collection",
            side_effect=mock_get_or_create_collection,
        ):
            yield mock_collection

    @pytest_asyncio.fixture(autouse=True)
    async def _mock_textract(self) -> AsyncGenerator[mock.MagicMock, None]:
        with mock.patch("flows.process_source.textract.process") as mock_textract:
            mock_textract.return_value = b"Sample source content for testing purposes"
            yield mock_textract

    @pytest.mark.asyncio
    async def test_success(self, test_session: AsyncSession):
        source = await SourceFactory.create_async(session=self.session)
        mock_context_manager = mock.AsyncMock()
        mock_context_manager.__aenter__.return_value = test_session
        mock_context_manager.__aexit__.return_value = None
        mock_async_session = mock.Mock(return_value=mock_context_manager)

        with mock.patch("flows.process_source.async_session", mock_async_session):
            chunks = await _index_source.fn(source_id=source.id)

            assert isinstance(chunks, list)
            assert len(chunks) > 0
            assert all(isinstance(chunk, str) for chunk in chunks)


class TestSummarizeSourceTask(BaseTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def _mock_summarize(self) -> AsyncGenerator[mock.MagicMock, None]:
        with mock.patch("flows.process_source.summarize") as mock_summarize:
            mock_summarize.return_value = "Mocked summary for chunk"
            yield mock_summarize

    @pytest.mark.asyncio
    async def test_success(self):
        test_chunks = [
            "This is the first chunk of the source.",
            "This is the second chunk of the source.",
            "This is the third chunk of the source.",
        ]

        summary = await _summarize_source.fn(chunks=test_chunks)

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

        with mock.patch("flows.process_source.async_session", mock_async_session):
            await _complete_processing_source.fn(
                source_id=source.id, summary=test_summary
            )

            await self.session.refresh(source)
            assert source.status == SourceStatus.COMPLETED
            assert source.summary == test_summary
