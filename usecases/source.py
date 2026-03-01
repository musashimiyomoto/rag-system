import json
import uuid
from pathlib import Path
from typing import Any, BinaryIO

from prefect.deployments import run_deployment
from sqlalchemy.ext.asyncio import AsyncSession

from ai.vector_store import delete_collection, delete_points
from db.connectors import (
    SourceDbConnectorError,
    introspect_clickhouse,
    introspect_postgres,
)
from db.repositories import (
    SessionSourceRepository,
    SourceDbRepository,
    SourceFileRepository,
    SourceRepository,
)
from enums import SourceStatus, SourceType
from exceptions import (
    SourceConflictError,
    SourceConnectionError,
    SourceNotFoundError,
    SourceNotSupportedError,
    SourceTooLargeError,
    SourceValidationError,
)
from flows import deploy_process_source_flow
from schemas import (
    DbSourceCreateRequest,
    DbSourceIntrospectRequest,
    DbSourceIntrospectResponse,
    DbTableSchema,
    SourceResponse,
)
from settings import core_settings
from utils import encrypt


class SourceUsecase:
    """Business logic for file and database sources."""

    def __init__(self):
        self._session_source_repository = SessionSourceRepository()
        self._source_repository = SourceRepository()
        self._source_file_repository = SourceFileRepository()
        self._source_db_repository = SourceDbRepository()

    def _validate_source(
        self, file_size: int | None, filename: str | None
    ) -> SourceType:
        """Validate uploaded file metadata and resolve source type.

        Args:
            file_size: Uploaded file size in bytes.
            filename: Uploaded file name with extension.

        Returns:
            Validated source type derived from the file extension.

        Raises:
            SourceTooLargeError: If file size is missing or exceeds the limit.
            SourceNotSupportedError: If extension is missing or unsupported.

        """
        if not file_size or file_size > core_settings.max_file_size:
            raise SourceTooLargeError

        file_type = (
            Path(filename).suffix.lower().removeprefix(".") if filename else None
        )
        if not file_type:
            raise SourceNotSupportedError

        try:
            source_type = SourceType(file_type)
        except ValueError as exc:
            raise SourceNotSupportedError from exc

        if source_type not in SourceType.get_file_types():
            raise SourceNotSupportedError

        return source_type

    @staticmethod
    def _build_collection_name(prefix: str) -> str:
        """Build a unique vector collection name for a source.

        Args:
            prefix: Source family prefix (`file` or `db`).

        Returns:
            Unique collection name with UUID suffix.

        """
        return f"{prefix}_{uuid.uuid4().hex}"

    @staticmethod
    def _validate_db_source_type(source_type: SourceType) -> None:
        """Ensure source type is allowed for DB-backed sources.

        Args:
            source_type: Requested source type.

        Raises:
            SourceValidationError: If type is not supported for DB sources.

        """
        if source_type not in SourceType.get_db_types():
            msg = "DB source type must be postgres or clickhouse"
            raise SourceValidationError(message=msg)

    @staticmethod
    async def _introspect_db(
        source_type: SourceType,
        credentials: dict[str, Any],
        schema_filter: str | None,
    ) -> list[dict[str, Any]]:
        """Introspect DB schema using the connector for the source type.

        Args:
            source_type: Database source type.
            credentials: Connection credentials for the DB.
            schema_filter: Optional schema name to limit introspection.

        Returns:
            Raw table metadata returned by connector introspection.

        Raises:
            SourceValidationError: If source type is not a supported DB type.

        """
        if source_type == SourceType.POSTGRES:
            return await introspect_postgres(
                credentials=credentials, schema_filter=schema_filter
            )
        if source_type == SourceType.CLICKHOUSE:
            return await introspect_clickhouse(
                credentials=credentials, schema_filter=schema_filter
            )

        msg = f"Unsupported DB source type: {source_type.value}"
        raise SourceValidationError(message=msg)

    @staticmethod
    def _find_table_schema(
        tables: list[dict[str, Any]], schema_name: str, table_name: str
    ) -> dict[str, Any]:
        """Find a table description in introspection payload.

        Args:
            tables: Introspection result containing table metadata.
            schema_name: Schema name to match.
            table_name: Table name to match.

        Returns:
            Table metadata dict for the requested table.

        Raises:
            SourceValidationError: If the table is not found.

        """
        for table in tables:
            if table["schema"] == schema_name and table["table"] == table_name:
                return table

        msg = f"Table {schema_name}.{table_name} not found"
        raise SourceValidationError(message=msg)

    @staticmethod
    def _validate_field_mapping(
        table: dict[str, Any],
        id_field: str,
        search_field: str,
        filter_fields: list[str],
    ) -> None:
        """Validate configured field mapping against table columns.

        Args:
            table: Introspected table metadata with column definitions.
            id_field: Column name used as unique identifier.
            search_field: Column name used for text indexing.
            filter_fields: Column names allowed for metadata filters.

        Raises:
            SourceValidationError: If unknown fields are used or duplicates exist.

        """
        available_fields = {
            str(column["name"])
            for column in table["columns"]
            if isinstance(column, dict) and "name" in column
        }

        unknown = [
            field
            for field in [id_field, search_field, *filter_fields]
            if field not in available_fields
        ]
        if len(unknown) > 0:
            msg = f"Unknown fields in mapping: {', '.join(sorted(set(unknown)))}"
            raise SourceValidationError(message=msg)

        if len(filter_fields) != len(set(filter_fields)):
            msg = "Duplicate filter fields are not allowed"
            raise SourceValidationError(message=msg)

    async def create_source(
        self,
        session: AsyncSession,
        file: BinaryIO,
        file_size: int | None,
        filename: str | None,
    ) -> SourceResponse:
        """Create a file source record and persist file content.

        Args:
            session: Database session.
            file: Uploaded file stream.
            file_size: Uploaded file size in bytes.
            filename: Uploaded file name.

        Returns:
            Created source response.

        """
        source = await self._source_repository.create(
            session=session,
            data={
                "name": filename,
                "type": self._validate_source(file_size=file_size, filename=filename),
                "status": SourceStatus.CREATED,
                "collection": self._build_collection_name(prefix="file"),
                "summary": None,
            },
        )

        await self._source_file_repository.create(
            session=session,
            data={"source_id": source.id, "content": file.read()},
        )

        return SourceResponse.model_validate(source)

    async def introspect_db_source(
        self, data: DbSourceIntrospectRequest
    ) -> DbSourceIntrospectResponse:
        """Introspect a DB source and return available schema metadata.

        Args:
            data: Introspection request with source type and credentials.

        Returns:
            Available tables and columns for the connection.

        Raises:
            SourceConnectionError: If DB connection or introspection fails.

        """
        self._validate_db_source_type(source_type=data.type)

        try:
            tables = await self._introspect_db(
                source_type=data.type,
                credentials=data.credentials.model_dump(),
                schema_filter=data.schema_name,
            )
        except SourceDbConnectorError as exc:
            raise SourceConnectionError(message=str(exc)) from exc

        return DbSourceIntrospectResponse(
            tables=[DbTableSchema.model_validate(table) for table in tables]
        )

    async def create_db_source(
        self,
        session: AsyncSession,
        data: DbSourceCreateRequest,
    ) -> SourceResponse:
        """Create a DB source with validated connection and field mapping.

        Args:
            session: Database session.
            data: DB source creation payload.

        Returns:
            Created DB source response.

        Raises:
            SourceConnectionError: If DB introspection fails.
            SourceValidationError: If selected table or fields are invalid.

        """
        self._validate_db_source_type(source_type=data.type)

        try:
            tables = await self._introspect_db(
                source_type=data.type,
                credentials=data.credentials.model_dump(),
                schema_filter=data.schema_name,
            )
        except SourceDbConnectorError as exc:
            raise SourceConnectionError(message=str(exc)) from exc

        table = self._find_table_schema(
            tables=tables,
            schema_name=data.schema_name,
            table_name=data.table_name,
        )
        self._validate_field_mapping(
            table=table,
            id_field=data.id_field,
            search_field=data.search_field,
            filter_fields=data.filter_fields,
        )

        source_name = (
            data.name or f"{data.type.value}:{data.schema_name}.{data.table_name}"
        )
        source = await self._source_repository.create(
            session=session,
            data={
                "name": source_name,
                "type": data.type,
                "status": SourceStatus.CREATED,
                "collection": self._build_collection_name(prefix="db"),
                "summary": None,
            },
        )

        await self._source_db_repository.create(
            session=session,
            data={
                "source_id": source.id,
                "db_type": data.type,
                "connection_encrypted": encrypt(
                    data=json.dumps(data.credentials.model_dump())
                ),
                "schema_name": data.schema_name,
                "table_name": data.table_name,
                "id_field": data.id_field,
                "search_field": data.search_field,
                "filter_fields": data.filter_fields,
            },
        )

        return SourceResponse.model_validate(source)

    @staticmethod
    async def deploy_process_source_flow(source_id: int) -> None:
        """Trigger Prefect deployment for source processing.

        Args:
            source_id: Source identifier to process.

        """
        await run_deployment(name=await deploy_process_source_flow(source_id=source_id))  # ty:ignore[invalid-await]

    async def get_sources(self, session: AsyncSession) -> list[SourceResponse]:
        """Return all sources.

        Args:
            session: Database session.

        Returns:
            List of all source responses.

        """
        return [
            SourceResponse.model_validate(source)
            for source in await self._source_repository.get_all(session=session)
        ]

    def get_supported_source_types(self) -> list[str]:
        """Return supported uploaded file source types.

        Returns:
            List of supported file source type values.

        """
        return [source_type.value for source_type in SourceType.get_file_types()]

    async def get_source(self, session: AsyncSession, source_id: int) -> SourceResponse:
        """Get a source by identifier.

        Args:
            session: Database session.
            source_id: Source identifier.

        Returns:
            Source response.

        Raises:
            SourceNotFoundError: If source does not exist.

        """
        source = await self._source_repository.get_by(session=session, id=source_id)
        if not source:
            raise SourceNotFoundError

        return SourceResponse.model_validate(source)

    async def delete_source(self, session: AsyncSession, id: int) -> None:
        """Delete a source and related vector data.

        Args:
            session: Database session.
            id: Source identifier.

        Raises:
            SourceNotFoundError: If source does not exist.
            SourceConflictError: If source is attached to one or more sessions.

        """
        source = await self._source_repository.get_by(session=session, id=id)
        if not source:
            raise SourceNotFoundError

        if await self._session_source_repository.get_by(session=session, source_id=id):
            raise SourceConflictError(
                message="Source is used by one or more sessions and cannot be deleted"
            )

        await delete_collection(name=source.collection)
        await delete_points(
            collection=core_settings.sources_index_collection, ids=[f"source-{id}"]
        )

        await self._source_repository.delete_by(session=session, id=id)
