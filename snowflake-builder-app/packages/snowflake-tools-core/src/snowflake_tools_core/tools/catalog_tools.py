"""Catalog exploration tools for Snowflake (databases, schemas, tables)."""

from __future__ import annotations

import json
from typing import Any

from snowflake_tools_core.client import SnowflakeClient


def list_databases() -> str:
    """List all databases accessible to the current role.

    Returns:
        JSON string with database names, owners, and creation dates.
    """
    client = SnowflakeClient()
    result = client.execute_query("SHOW DATABASES")
    databases = [
        {"name": row[1], "owner": row[5], "created": str(row[0])}
        for row in result["rows"]
    ]
    return json.dumps({"databases": databases, "count": len(databases)}, default=str)


def list_schemas(database: str) -> str:
    """List all schemas in a database.

    Args:
        database: The database to list schemas for.

    Returns:
        JSON string with schema names and owners.
    """
    client = SnowflakeClient()
    result = client.execute_query(f"SHOW SCHEMAS IN DATABASE {database}")
    schemas = [
        {"name": row[1], "owner": row[5], "created": str(row[0])}
        for row in result["rows"]
    ]
    return json.dumps({"schemas": schemas, "count": len(schemas), "database": database}, default=str)


def list_tables(database: str, schema: str) -> str:
    """List all tables and views in a schema.

    Args:
        database: The database containing the schema.
        schema: The schema to list tables for.

    Returns:
        JSON string with table names, types, row counts.
    """
    client = SnowflakeClient()
    result = client.execute_query(f"SHOW TABLES IN {database}.{schema}")
    tables = [
        {
            "name": row[1],
            "kind": row[3] if len(row) > 3 else "TABLE",
            "rows": row[6] if len(row) > 6 else None,
            "owner": row[5] if len(row) > 5 else None,
        }
        for row in result["rows"]
    ]

    # Also get views
    try:
        view_result = client.execute_query(f"SHOW VIEWS IN {database}.{schema}")
        views = [
            {"name": row[1], "kind": "VIEW", "rows": None, "owner": row[5] if len(row) > 5 else None}
            for row in view_result["rows"]
        ]
        tables.extend(views)
    except Exception:
        pass  # Views query may fail if no views exist

    return json.dumps(
        {"objects": tables, "count": len(tables), "database": database, "schema": schema},
        default=str,
    )


def describe_table(database: str, schema: str, table: str) -> str:
    """Describe a table's columns and their types.

    Args:
        database: The database containing the table.
        schema: The schema containing the table.
        table: The table name to describe.

    Returns:
        JSON string with column names, types, nullability, and comments.
    """
    client = SnowflakeClient()
    fqn = f"{database}.{schema}.{table}"
    result = client.execute_query(f"DESCRIBE TABLE {fqn}")
    columns = [
        {
            "name": row[0],
            "type": row[1],
            "nullable": row[3] == "Y" if len(row) > 3 else True,
            "default": row[4] if len(row) > 4 else None,
            "comment": row[8] if len(row) > 8 else None,
        }
        for row in result["rows"]
    ]
    return json.dumps({"table": fqn, "columns": columns, "column_count": len(columns)}, default=str)


def get_ddl(object_type: str, database: str, schema: str, name: str) -> str:
    """Get the DDL (CREATE statement) for a Snowflake object.

    Args:
        object_type: The object type (TABLE, VIEW, FUNCTION, PROCEDURE, TASK, etc.).
        database: The database containing the object.
        schema: The schema containing the object.
        name: The object name.

    Returns:
        The DDL statement as a string.
    """
    client = SnowflakeClient()
    fqn = f"{database}.{schema}.{name}"
    result = client.execute_query(f"SELECT GET_DDL('{object_type}', '{fqn}')")
    if result["rows"]:
        return result["rows"][0][0]
    return f"No DDL found for {object_type} {fqn}"
