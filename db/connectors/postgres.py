from collections.abc import AsyncIterator, Mapping
from typing import Any

import asyncpg

from db.connectors.common import SourceDbConnectorError, validate_identifier


def _quote_postgres_identifier(value: str) -> str:
    """Quote and validate a PostgreSQL identifier.

    Args:
        value: Identifier value to quote.

    Returns:
        Double-quoted validated identifier.

    """
    return f'"{validate_identifier(value=value, field_name="identifier")}"'


def _postgres_ssl_value(sslmode: str | None) -> bool | None:
    """Map PostgreSQL `sslmode` to asyncpg `ssl` argument.

    Args:
        sslmode: PostgreSQL SSL mode string.

    Returns:
        `None` to use asyncpg default, `False` for `disable`, otherwise `True`.

    """
    if sslmode is None:
        return None

    return sslmode.lower() != "disable"


async def introspect_postgres(
    credentials: Mapping[str, Any], schema_filter: str | None
) -> list[dict[str, Any]]:
    """Introspect PostgreSQL table and column metadata.

    Args:
        credentials: Connection settings for PostgreSQL.
        schema_filter: Optional schema name to limit results.

    Returns:
        Table metadata grouped by schema and table name.

    Raises:
        SourceDbConnectorError: If connection or query execution fails.

    """
    params = [schema_filter] if schema_filter else []
    query = """
        SELECT
            c.table_schema,
            c.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable
        FROM information_schema.columns AS c
        JOIN information_schema.tables AS t
          ON c.table_schema = t.table_schema
         AND c.table_name = t.table_name
        WHERE t.table_type = 'BASE TABLE'
          AND c.table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY c.table_schema, c.table_name, c.ordinal_position
    """
    if schema_filter:
        query = query.replace(
            "ORDER BY",
            "AND c.table_schema = $1\n        ORDER BY",
        )

    conn = await asyncpg.connect(
        host=str(credentials["host"]),
        port=int(credentials["port"]),
        database=str(credentials["database"]),
        user=str(credentials["user"]),
        password=str(credentials["password"]),
        ssl=_postgres_ssl_value(credentials.get("sslmode")),
    )
    try:
        rows = await conn.fetch(query, *params)
    except Exception as exc:  # noqa: BLE001
        raise SourceDbConnectorError(str(exc)) from exc
    finally:
        await conn.close()

    tables: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        schema_name = str(row["table_schema"])
        table_name = str(row["table_name"])
        key = (schema_name, table_name)
        if key not in tables:
            tables[key] = {
                "schema": schema_name,
                "table": table_name,
                "columns": [],
            }

        tables[key]["columns"].append(
            {
                "name": str(row["column_name"]),
                "type": str(row["data_type"]),
                "nullable": str(row["is_nullable"]).upper() == "YES",
            }
        )

    return list(tables.values())


async def stream_postgres_rows(
    credentials: Mapping[str, Any],
    schema_name: str,
    table_name: str,
    columns: list[str],
    batch_size: int = 500,
) -> AsyncIterator[list[dict[str, Any]]]:
    """Stream PostgreSQL rows in fixed-size batches.

    Args:
        credentials: Connection settings for PostgreSQL.
        schema_name: Source schema name.
        table_name: Source table name.
        columns: List of column names to select.
        batch_size: Maximum number of rows per yielded batch.

    Yields:
        Row batches represented as lists of dictionaries.

    Raises:
        SourceDbConnectorError: If connection or query execution fails.

    """
    validated_columns = [
        _quote_postgres_identifier(validate_identifier(column, "column"))
        for column in columns
    ]
    quoted_schema = _quote_postgres_identifier(
        validate_identifier(schema_name, "schema")
    )
    quoted_table = _quote_postgres_identifier(validate_identifier(table_name, "table"))

    query = (
        f"SELECT {', '.join(validated_columns)} "  # noqa: S608
        f"FROM {quoted_schema}.{quoted_table} LIMIT $1 OFFSET $2"
    )

    conn = await asyncpg.connect(
        host=str(credentials["host"]),
        port=int(credentials["port"]),
        database=str(credentials["database"]),
        user=str(credentials["user"]),
        password=str(credentials["password"]),
        ssl=_postgres_ssl_value(credentials.get("sslmode")),
    )

    offset = 0
    try:
        while True:
            rows = await conn.fetch(query, batch_size, offset)
            if len(rows) == 0:
                break

            payload = [dict(row) for row in rows]
            yield payload

            offset += len(payload)
    except Exception as exc:  # noqa: BLE001
        raise SourceDbConnectorError(str(exc)) from exc
    finally:
        await conn.close()
