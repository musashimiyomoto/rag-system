import io
from http import HTTPStatus
from typing import AsyncGenerator
from unittest import mock

import pytest
import pytest_asyncio
from fastapi import UploadFile
from sqlalchemy import select

from db.models import SourceFile
from enums import SourceStatus, SourceType
from tests.base import BaseTestCase
from tests.factories import SessionFactory, SessionSourceFactory, SourceFactory


class TestCreateSource(BaseTestCase):
    url = "/source"

    @pytest_asyncio.fixture(autouse=True)
    async def _mock_prefect_deployment(self) -> AsyncGenerator[mock.MagicMock, None]:
        async def mock_deploy_process_source_flow(source_id: int) -> None:
            return None

        with mock.patch(
            "usecases.source.SourceUsecase.deploy_process_source_flow"
        ) as mock_deploy:
            mock_deploy.side_effect = mock_deploy_process_source_flow
            yield mock_deploy

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        source_name = "test.pdf"
        source_type = SourceType.PDF
        file_content = b"Test PDF content"
        file = UploadFile(
            file=io.BytesIO(file_content),
            filename=source_name,
            size=len(file_content),
        )

        response = await self.client.post(
            url=self.url, files={"file": (file.filename, file.file, "application/pdf")}
        )

        data = await self.assert_response_ok(response=response)
        assert data["id"] is not None
        assert data["name"] == source_name
        assert data["type"] == source_type.value
        assert data["status"] == SourceStatus.CREATED.value
        assert data["collection"] is not None
        assert data["created_at"] is not None
        assert data["updated_at"] is not None

        source_file = (
            await self.session.execute(
                select(SourceFile).where(SourceFile.source_id == data["id"])
            )
        ).scalar_one_or_none()

        assert source_file is not None
        assert source_file.content == file_content


class TestGetSources(BaseTestCase):
    url = "/source/list"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        source_count = 2
        [
            await SourceFactory.create_async(session=self.session)
            for _ in range(source_count)
        ]

        response = await self.client.get(url=self.url)

        data = await self.assert_response_ok(response=response)
        assert isinstance(data, list)
        assert len(data) == source_count


class TestGetSource(BaseTestCase):
    url = "/source/{source_id}"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        source = await SourceFactory.create_async(session=self.session)

        response = await self.client.get(url=self.url.format(source_id=source.id))

        data = await self.assert_response_ok(response=response)
        assert data["id"] == source.id
        assert data["name"] == source.name
        assert data["type"] == source.type.value
        assert data["status"] == source.status.value
        assert data["collection"] == source.collection


class TestGetSessionsForSource(BaseTestCase):
    url = "/source/{source_id}/session/list"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        session_count = 2
        source = await SourceFactory.create_async(session=self.session)
        sessions = [
            await SessionFactory.create_async(session=self.session)
            for _ in range(session_count)
        ]
        [
            await SessionSourceFactory.create_async(
                session=self.session, session_id=session.id, source_id=source.id
            )
            for session in sessions
        ]

        response = await self.client.get(url=self.url.format(source_id=source.id))

        data = await self.assert_response_ok(response=response)
        assert isinstance(data, list)
        assert len(data) == session_count


class TestDeleteSource(BaseTestCase):
    url = "/source/{id}"

    @pytest_asyncio.fixture(autouse=True)
    async def _mock_chroma(self) -> AsyncGenerator[mock.MagicMock, None]:
        mock_client = mock.AsyncMock()
        mock_client.get_or_create_collection.return_value = mock.AsyncMock()
        mock_client.delete_collection.return_value = None

        with mock.patch("chromadb.AsyncHttpClient", return_value=mock_client):
            yield mock_client

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        source = await SourceFactory.create_async(session=self.session)

        response = await self.client.delete(url=self.url.format(id=source.id))

        await self.assert_response_ok(response=response)

    @pytest.mark.asyncio
    async def test_source_used_in_session_returns_409(self) -> None:
        source = await SourceFactory.create_async(session=self.session)
        chat_session = await SessionFactory.create_async(session=self.session)
        await SessionSourceFactory.create_async(
            session=self.session, session_id=chat_session.id, source_id=source.id
        )

        response = await self.client.delete(url=self.url.format(id=source.id))

        assert response.status_code == HTTPStatus.CONFLICT
