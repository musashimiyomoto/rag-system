import io
from typing import AsyncGenerator
from unittest import mock

import pytest
import pytest_asyncio
from fastapi import UploadFile

from enums import DocumentStatus, DocumentType
from tests.base import BaseTestCase
from tests.factories import DocumentFactory, SessionFactory


class TestCreateDocument(BaseTestCase):
    url = "/document"

    @pytest_asyncio.fixture(autouse=True)
    async def _mock_redis(self) -> AsyncGenerator[mock.MagicMock, None]:
        async def mock_set(name: str, value: str) -> None:
            return None

        with mock.patch("usecases.document.redis_client") as mock_redis:
            mock_redis.set.side_effect = mock_set
            yield mock_redis

    @pytest_asyncio.fixture(autouse=True)
    async def _mock_prefect_deployment(self) -> AsyncGenerator[mock.MagicMock, None]:
        async def mock_deploy_process_document_flow(document_id: int) -> None:
            return None

        with mock.patch(
            "usecases.document.DocumentUsecase.deploy_process_document_flow"
        ) as mock_deploy:
            mock_deploy.side_effect = mock_deploy_process_document_flow
            yield mock_deploy

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        document_name = "test.pdf"
        document_type = DocumentType.PDF
        file_content = b"Test PDF content"
        file = UploadFile(
            file=io.BytesIO(file_content),
            filename=document_name,
            size=len(file_content),
        )

        response = await self.client.post(
            url=self.url, files={"file": (file.filename, file.file, "application/pdf")}
        )

        data = await self.assert_response_ok(response=response)
        assert data["id"] is not None
        assert data["name"] == document_name
        assert data["type"] == document_type.value
        assert data["status"] == DocumentStatus.CREATED.value
        assert data["collection"] is not None
        assert data["created_at"] is not None
        assert data["updated_at"] is not None


class TestGetDocuments(BaseTestCase):
    url = "/document/list"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        document_count = 2
        [
            await DocumentFactory.create_async(session=self.session)
            for _ in range(document_count)
        ]

        response = await self.client.get(url=self.url)

        data = await self.assert_response_ok(response=response)
        assert isinstance(data, list)
        assert len(data) == document_count


class TestGetDocument(BaseTestCase):
    url = "/document/{document_id}"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        document = await DocumentFactory.create_async(session=self.session)

        response = await self.client.get(url=self.url.format(document_id=document.id))

        data = await self.assert_response_ok(response=response)
        assert data["id"] == document.id
        assert data["name"] == document.name
        assert data["type"] == document.type.value
        assert data["status"] == document.status.value
        assert data["collection"] == document.collection


class TestGetSessionsForDocument(BaseTestCase):
    url = "/document/{document_id}/session/list"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        session_count = 2
        document = await DocumentFactory.create_async(session=self.session)
        [
            await SessionFactory.create_async(
                session=self.session, document_id=document.id
            )
            for _ in range(session_count)
        ]

        response = await self.client.get(url=self.url.format(document_id=document.id))

        data = await self.assert_response_ok(response=response)
        assert isinstance(data, list)
        assert len(data) == session_count


class TestDeleteDocument(BaseTestCase):
    url = "/document/{id}"

    @pytest_asyncio.fixture(autouse=True)
    async def _mock_chroma(self) -> AsyncGenerator[mock.MagicMock, None]:
        async def mock_delete_collection(name: str) -> None:
            return None

        with mock.patch("chromadb.AsyncHttpClient") as mock_chroma:
            mock_chroma.delete_collection.side_effect = mock_delete_collection
            yield mock_chroma

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        document = await DocumentFactory.create_async(session=self.session)

        response = await self.client.delete(url=self.url.format(id=document.id))

        await self.assert_response_ok(response=response)
