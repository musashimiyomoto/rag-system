import uuid
from pathlib import Path
from typing import BinaryIO

import chromadb
from prefect.deployments import run_deployment
from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import (
    SessionSourceRepository,
    SourceFileRepository,
    SourceRepository,
)
from enums import SourceStatus, SourceType
from exceptions import (
    SourceConflictError,
    SourceNotFoundError,
    SourceNotSupportedError,
    SourceTooLargeError,
)
from flows import deploy_process_source_flow
from schemas import SourceResponse
from settings import chroma_settings, core_settings


class SourceUsecase:
    def __init__(self):
        self._session_source_repository = SessionSourceRepository()
        self._source_repository = SourceRepository()
        self._source_file_repository = SourceFileRepository()

    def _validate_source(
        self, file_size: int | None, filename: str | None
    ) -> SourceType:
        """Validate the source.

        Args:
            file: The file.
            file_size: The file size.
            filename: The filename.

        Returns:
            None.

        """
        if not file_size or file_size > core_settings.max_file_size:
            raise SourceTooLargeError

        file_type = (
            Path(filename).suffix.lower().removeprefix(".") if filename else None
        )
        if not file_type or file_type not in list(SourceType):
            raise SourceNotSupportedError

        return SourceType(file_type)

    async def create_source(
        self,
        session: AsyncSession,
        file: BinaryIO,
        file_size: int | None,
        filename: str | None,
    ) -> SourceResponse:
        """Create a new source.

        Args:
            session: The async session.
            file: The file.
            file_size: The file size.
            filename: The filename.

        Returns:
            The created source.

        """
        source = await self._source_repository.create(
            session=session,
            data={
                "name": filename,
                "type": self._validate_source(file_size=file_size, filename=filename),
                "status": SourceStatus.CREATED,
                "collection": uuid.uuid4().hex,
                "summary": None,
            },
        )

        await self._source_file_repository.create(
            session=session,
            data={"source_id": source.id, "content": file.read()},
        )

        return SourceResponse.model_validate(source)

    @staticmethod
    async def deploy_process_source_flow(source_id: int) -> None:
        """Deploy the process source flow.

        Args:
            source_id: The source ID.

        """
        await run_deployment(name=await deploy_process_source_flow(source_id=source_id))  # ty:ignore[invalid-await]

    async def get_sources(self, session: AsyncSession) -> list[SourceResponse]:
        """Get the sources.

        Args:
            session: The async session.

        Returns:
            The sources.

        """
        return [
            SourceResponse.model_validate(source)
            for source in await self._source_repository.get_all(session=session)
        ]

    async def get_source(self, session: AsyncSession, source_id: int) -> SourceResponse:
        """Get a source by ID.

        Args:
            session: The async session.
            source_id: The source ID.

        Returns:
            The source.

        """
        source = await self._source_repository.get_by(session=session, id=source_id)
        if not source:
            raise SourceNotFoundError

        return SourceResponse.model_validate(source)

    async def delete_source(self, session: AsyncSession, id: int) -> None:
        """Delete the source.

        Args:
            session: The async session.
            id: The source ID.

        """
        source = await self._source_repository.get_by(session=session, id=id)
        if not source:
            raise SourceNotFoundError

        if await self._session_source_repository.get_by(session=session, source_id=id):
            raise SourceConflictError(
                message="Source is used by one or more sessions and cannot be deleted"
            )

        chroma_client = await chromadb.AsyncHttpClient(
            host=chroma_settings.host,
            port=chroma_settings.port,
        )

        if await chroma_client.get_or_create_collection(name=source.collection):
            await chroma_client.delete_collection(name=source.collection)

        source_index = await chroma_client.get_or_create_collection(
            name=core_settings.sources_index_collection
        )
        await source_index.delete(ids=[f"source-{id}"])

        await self._source_repository.delete_by(session=session, id=id)
