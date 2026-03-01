import asyncio
from collections.abc import AsyncIterator, Mapping
from typing import Any

import clickhouse_connect

from db.connectors.common import SourceDbConnectorError, validate_identifier


def _quote_clickhouse_identifier(value: str) -> str:
    """Quote and validate a ClickHouse identifier.

    Args:
        value: Identifier value to quote.

    Returns:
        Backtick-quoted validated identifier.

    """
    return f"`{validate_identifier(value=value, field_name='identifier')}`"


async def introspect_clickhouse(
    credentials: Mapping[str, Any], schema_filter: str | None
) -> list[dict[str, Any]]:
    """Introspect ClickHouse table and column metadata.

    Args:
        credentials: Connection settings for ClickHouse.
        schema_filter: Optional database name to limit results.

    Returns:
        Table metadata grouped by schema and table name.

    Raises:
        SourceDbConnectorError: If connection or query execution fails.

    """

    def _query() -> list[tuple[Any, ...]]:
        client = clickhouse_connect.get_client(
            host=str(credentials["host"]),
            port=int(credentials["port"]),
            username=str(credentials["user"]),
            password=str(credentials["password"]),
            database=str(credentials["database"]),
            secure=bool(credentials.get("secure", False)),
        )

        if schema_filter:
            result = client.query(
                """
                SELECT database, table, name, type
                FROM system.columns
                WHERE database = %(schema)s
                ORDER BY database, table, position
                """,
                parameters={"schema": schema_filter},
            )
        else:
            result = client.query(
                """
                SELECT database, table, name, type
                FROM system.columns
                WHERE database NOT IN (
                    'system',
                    'information_schema',
                    'INFORMATION_SCHEMA'
                )
                ORDER BY database, table, position
                """
            )
        return result.result_rows

    try:
        rows = await asyncio.to_thread(_query)
    except Exception as exc:  # noqa: BLE001
        raise SourceDbConnectorError(str(exc)) from exc

    tables: dict[tuple[str, str], dict[str, Any]] = {}
    for schema_name, table_name, column_name, column_type in rows:
        key = (str(schema_name), str(table_name))
        if key not in tables:
            tables[key] = {
                "schema": str(schema_name),
                "table": str(table_name),
                "columns": [],
            }

        type_name = str(column_type)
        tables[key]["columns"].append(
            {
                "name": str(column_name),
                "type": type_name,
                "nullable": type_name.startswith("Nullable("),
            }
        )

    return list(tables.values())


async def stream_clickhouse_rows(
    credentials: Mapping[str, Any],
    schema_name: str,
    table_name: str,
    columns: list[str],
    batch_size: int = 500,
) -> AsyncIterator[list[dict[str, Any]]]:
    """Stream ClickHouse rows in fixed-size batches.

    Args:
        credentials: Connection settings for ClickHouse.
        schema_name: Source database name.
        table_name: Source table name.
        columns: List of column names to select.
        batch_size: Maximum number of rows per yielded batch.

    Yields:
        Row batches represented as lists of dictionaries.

    Raises:
        SourceDbConnectorError: If connection or query execution fails.

    """
    validated_columns = [
        _quote_clickhouse_identifier(validate_identifier(column, "column"))
        for column in columns
    ]
    quoted_schema = _quote_clickhouse_identifier(
        validate_identifier(schema_name, "schema")
    )
    quoted_table = _quote_clickhouse_identifier(
        validate_identifier(table_name, "table")
    )

    query = (
        f"SELECT {', '.join(validated_columns)} "  # noqa: S608
        f"FROM {quoted_schema}.{quoted_table} LIMIT %(limit)s OFFSET %(offset)s"
    )

    def _query_batch(offset: int) -> list[dict[str, Any]]:
        client = clickhouse_connect.get_client(
            host=str(credentials["host"]),
            port=int(credentials["port"]),
            username=str(credentials["user"]),
            password=str(credentials["password"]),
            database=str(credentials["database"]),
            secure=bool(credentials.get("secure", False)),
        )
        result = client.query(
            query,
            parameters={"limit": batch_size, "offset": offset},
        )
        return [
            dict(zip(result.column_names, row, strict=True))
            for row in result.result_rows
        ]

    offset = 0
    while True:
        try:
            rows = await asyncio.to_thread(_query_batch, offset)
        except Exception as exc:  # noqa: BLE001
            raise SourceDbConnectorError(str(exc)) from exc

        if len(rows) == 0:
            break

        yield rows
        offset += len(rows)
