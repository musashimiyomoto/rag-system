import io

import pytest
from fastapi import UploadFile

from enums import SourceType
from tests.base import BaseTestCase
from tests.factories import SourceFactory


class TestCreateSource(BaseTestCase):
    url = "/source"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("source_name", "source_type"),
        [
            ("test.md", SourceType.MD),
            ("test.docx", SourceType.DOCX),
            ("test.rtf", SourceType.RTF),
            ("test.odt", SourceType.ODT),
            ("test.epub", SourceType.EPUB),
            ("test.html", SourceType.HTML),
            ("test.htm", SourceType.HTM),
            ("test.pptx", SourceType.PPTX),
            ("test.xlsx", SourceType.XLSX),
            ("test.eml", SourceType.EML),
        ],
    )
    async def test_ok(self, source_name: str, source_type: SourceType) -> None:
        file_content = b"Sample content"
        file = UploadFile(
            file=io.BytesIO(file_content),
            filename=source_name,
            size=len(file_content),
        )

        response = await self.client.post(
            url=self.url,
            files={"file": (file.filename, file.file, "application/octet-stream")},
        )

        data = await self.assert_response_ok(response=response)
        assert data["name"] == source_name
        assert data["type"] == source_type.value


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


class TestGetSourceTypes(BaseTestCase):
    url = "/source/type/list"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        response = await self.client.get(url=self.url)

        data = await self.assert_response_ok(response=response)
        assert isinstance(data, list)
        assert SourceType.POSTGRES.value not in data
        assert SourceType.CLICKHOUSE.value not in data


class TestDeleteSource(BaseTestCase):
    url = "/source/{id}"

    @pytest.mark.asyncio
    async def test_ok(self) -> None:
        source = await SourceFactory.create_async(session=self.session)

        response = await self.client.delete(url=self.url.format(id=source.id))

        await self.assert_response_ok(response=response)
