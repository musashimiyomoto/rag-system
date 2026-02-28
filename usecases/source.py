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
from flows.deployment import deploy_process_source_flow
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
    def __init__(self):
        self._session_source_repository = SessionSourceRepository()
        self._source_repository = SourceRepository()
        self._source_file_repository = SourceFileRepository()
        self._source_db_repository = SourceDbRepository()

    def _validate_source(
        self, file_size: int | None, filename: str | None
    ) -> SourceType:
        """Validate uploaded source file extension and size."""
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
        """Build stable collection name prefix for source storage."""
        return f"{prefix}_{uuid.uuid4().hex}"

    @staticmethod
    def _validate_db_source_type(source_type: SourceType) -> None:
        """Validate source type for DB operations."""
        if source_type not in SourceType.get_db_types():
            msg = "DB source type must be postgres or clickhouse"
            raise SourceValidationError(message=msg)

    @staticmethod
    async def _introspect_db(
        source_type: SourceType,
        credentials: dict[str, Any],
        schema_filter: str | None,
    ) -> list[dict[str, Any]]:
        """Run DB introspection for selected source type."""
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
        """Find table schema by name and validate it exists."""
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
        """Validate id/search/filter fields against table schema."""
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
        """Create a new file source."""
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
        """Introspect DB source and return available tables/columns."""
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
        """Create DB source with selected table field mapping."""
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
        """Deploy the process source flow."""
        await run_deployment(name=await deploy_process_source_flow(source_id=source_id))  # ty:ignore[invalid-await]

    async def get_sources(self, session: AsyncSession) -> list[SourceResponse]:
        """Get all sources."""
        return [
            SourceResponse.model_validate(source)
            for source in await self._source_repository.get_all(session=session)
        ]

    def get_supported_source_types(self) -> list[str]:
        """Get supported source types."""
        return [source_type.value for source_type in SourceType.get_file_types()]

    async def get_source(self, session: AsyncSession, source_id: int) -> SourceResponse:
        """Get source by ID."""
        source = await self._source_repository.get_by(session=session, id=source_id)
        if not source:
            raise SourceNotFoundError

        return SourceResponse.model_validate(source)

    async def delete_source(self, session: AsyncSession, id: int) -> None:
        """Delete source and its vectors."""
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
