"""Pipeline and scheduling tools for Snowflake (Tasks, Dynamic Tables, Streams)."""

from __future__ import annotations

import json
from typing import Any

from snowflake_tools_core.client import SnowflakeClient


def list_tasks(database: str | None = None, schema: str | None = None) -> str:
    """List Snowflake Tasks in the given scope.

    Args:
        database: Optional database to scope the listing.
        schema: Optional schema to scope the listing.

    Returns:
        JSON string with task names, schedules, states, and owners.
    """
    client = SnowflakeClient()
    scope = ""
    if database and schema:
        scope = f" IN {database}.{schema}"
    elif database:
        scope = f" IN DATABASE {database}"

    result = client.execute_query(f"SHOW TASKS{scope}")
    tasks = [
        {
            "name": row[1],
            "database": row[3] if len(row) > 3 else None,
            "schema": row[4] if len(row) > 4 else None,
            "schedule": row[7] if len(row) > 7 else None,
            "state": row[9] if len(row) > 9 else None,
            "owner": row[5] if len(row) > 5 else None,
        }
        for row in result["rows"]
    ]
    return json.dumps({"tasks": tasks, "count": len(tasks)}, default=str)


def list_dynamic_tables(database: str | None = None, schema: str | None = None) -> str:
    """List Snowflake Dynamic Tables in the given scope.

    Args:
        database: Optional database to scope the listing.
        schema: Optional schema to scope the listing.

    Returns:
        JSON string with dynamic table names, target lag, refresh mode.
    """
    client = SnowflakeClient()
    scope = ""
    if database and schema:
        scope = f" IN {database}.{schema}"
    elif database:
        scope = f" IN DATABASE {database}"

    result = client.execute_query(f"SHOW DYNAMIC TABLES{scope}")
    tables = [
        {
            "name": row[1],
            "database": row[3] if len(row) > 3 else None,
            "schema": row[4] if len(row) > 4 else None,
            "target_lag": row[7] if len(row) > 7 else None,
            "refresh_mode": row[8] if len(row) > 8 else None,
            "owner": row[5] if len(row) > 5 else None,
        }
        for row in result["rows"]
    ]
    return json.dumps({"dynamic_tables": tables, "count": len(tables)}, default=str)
