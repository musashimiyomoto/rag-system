import base64
import uuid
from pathlib import Path
from typing import BinaryIO

import chromadb
from prefect.deployments import run_deployment
from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import DocumentRepository, MessageRepository, SessionRepository
from enums import DocumentStatus, DocumentType
from exceptions import (
    DocumentNotFoundError,
    DocumentNotSupportedError,
    DocumentTooLargeError,
)
from flows import deploy_process_document_flow
from schemas import DocumentResponse
from settings import chroma_settings, core_settings
from utils import redis_client


class DocumentUsecase:
    def __init__(self):
        self._message_repository = MessageRepository()
        self._session_repository = SessionRepository()
        self._document_repository = DocumentRepository()

    def _validate_document(
        self, file_size: int | None, filename: str | None
    ) -> DocumentType:
        """Validate the document.

        Args:
            file: The file.
            file_size: The file size.
            filename: The filename.

        Returns:
            None.

        """
        if not file_size or file_size > core_settings.max_file_size:
            raise DocumentTooLargeError

        file_type = (
            Path(filename).suffix.lower().removeprefix(".") if filename else None
        )
        if not file_type or file_type not in list(DocumentType):
            raise DocumentNotSupportedError

        return DocumentType(file_type)

    async def create_document(
        self,
        session: AsyncSession,
        file: BinaryIO,
        file_size: int | None,
        filename: str | None,
    ) -> DocumentResponse:
        """Create a new document.

        Args:
            session: The async session.
            file: The file.
            file_size: The file size.
            filename: The filename.

        Returns:
            The created document.

        """
        collection = uuid.uuid4().hex

        file_content = file.read()
        encoded_content = base64.b64encode(file_content).decode("utf-8")
        await redis_client.set(name=collection, value=encoded_content)

        return DocumentResponse.model_validate(
            await self._document_repository.create(
                session=session,
                data={
                    "name": filename,
                    "type": self._validate_document(
                        file_size=file_size, filename=filename
                    ),
                    "status": DocumentStatus.CREATED,
                    "collection": collection,
                },
            )
        )

    @staticmethod
    async def deploy_process_document_flow(document_id: int) -> None:
        """Deploy the process document flow.

        Args:
            document_id: The document ID.

        """
        await run_deployment(
            name=await deploy_process_document_flow(document_id=document_id)
        )  # type: ignore[arg-type]

    async def get_documents(self, session: AsyncSession) -> list[DocumentResponse]:
        """Get the documents.

        Args:
            session: The async session.

        Returns:
            The documents.

        """
        return [
            DocumentResponse.model_validate(document)
            for document in await self._document_repository.get_all(session=session)
        ]

    async def get_document(
        self, session: AsyncSession, document_id: int
    ) -> DocumentResponse:
        """Get a document by ID.

        Args:
            session: The async session.
            document_id: The document ID.

        Returns:
            The document.

        """
        document = await self._document_repository.get_by(
            session=session, id=document_id
        )
        if not document:
            raise DocumentNotFoundError

        return DocumentResponse.model_validate(document)

    async def delete_document(self, session: AsyncSession, id: int) -> None:
        """Delete the document.

        Args:
            session: The async session.
            id: The document ID.

        """
        document = await self._document_repository.get_by(session=session, id=id)
        if not document:
            raise DocumentNotFoundError

        chroma_client = await chromadb.AsyncHttpClient(
            host=chroma_settings.host,
            port=chroma_settings.port,
        )

        if await chroma_client.get_or_create_collection(name=document.collection):
            await chroma_client.delete_collection(name=document.collection)

        for chat_session in await self._session_repository.get_all(
            session=session, document_id=id
        ):
            await self._message_repository.delete_all(
                session=session, session_id=chat_session.id
            )
            await self._session_repository.delete_by(
                session=session, id=chat_session.id
            )

        await self._document_repository.delete_by(session=session, id=id)
