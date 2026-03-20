"""SQL execution tools for Snowflake."""

from __future__ import annotations

import json
from typing import Any

from snowflake_tools_core.client import SnowflakeClient


def execute_sql(query: str, database: str | None = None, schema: str | None = None) -> str:
    """Execute a SQL query on Snowflake and return the results.

    Args:
        query: The SQL query to execute.
        database: Optional database context for the query.
        schema: Optional schema context for the query.

    Returns:
        JSON string with columns, rows, row_count, and query_id.
    """
    client = SnowflakeClient()
    full_query = ""
    if database:
        full_query += f"USE DATABASE {database};\n"
    if schema:
        full_query += f"USE SCHEMA {schema};\n"

    if full_query:
        # Execute context-setting statements first
        for stmt in full_query.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                client.execute_query(stmt)

    result = client.execute_query(query)

    # Format for readability
    if result["row_count"] == 0:
        return json.dumps({"message": "Query executed successfully. No rows returned.", "query_id": result["query_id"]})

    # Truncate large result sets
    max_rows = 50
    truncated = False
    rows = result["rows"]
    if len(rows) > max_rows:
        rows = rows[:max_rows]
        truncated = True

    output = {
        "columns": result["columns"],
        "rows": rows,
        "row_count": result["row_count"],
        "query_id": result["query_id"],
    }
    if truncated:
        output["note"] = f"Showing first {max_rows} of {result['row_count']} rows."

    return json.dumps(output, default=str)


def execute_sql_multi(queries: list[str]) -> str:
    """Execute multiple SQL statements and return all results.

    Args:
        queries: List of SQL statements to execute in order.

    Returns:
        JSON string with results for each statement.
    """
    client = SnowflakeClient()
    results = client.execute_multi(queries)
    return json.dumps(results, default=str)
