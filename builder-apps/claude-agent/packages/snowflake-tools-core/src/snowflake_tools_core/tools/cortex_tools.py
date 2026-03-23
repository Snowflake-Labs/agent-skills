"""Cortex AI tools for Snowflake (Complete, Search)."""

from __future__ import annotations

import json
from typing import Any

from snowflake_tools_core.client import SnowflakeClient


def cortex_complete(prompt: str, model: str = "claude-4-sonnet") -> str:
    """Run a Cortex AI completion.

    Args:
        prompt: The text prompt to send to the model.
        model: The model to use (default: claude-4-sonnet).

    Returns:
        The model's response text.
    """
    client = SnowflakeClient()
    # Escape single quotes in prompt
    escaped_prompt = prompt.replace("'", "''")
    result = client.execute_query(
        f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', '{escaped_prompt}')"
    )
    if result["rows"]:
        return result["rows"][0][0]
    return ""


def cortex_search(
    query: str,
    service_name: str,
    columns: list[str] | None = None,
    limit: int = 5,
) -> str:
    """Search using a Cortex Search Service.

    Args:
        query: The search query text.
        service_name: Fully-qualified Cortex Search Service name.
        columns: Optional list of columns to return.
        limit: Maximum number of results (default: 5).

    Returns:
        JSON string with search results.
    """
    client = SnowflakeClient()
    cols = ", ".join(columns) if columns else "*"
    escaped_query = query.replace("'", "''")

    # Use the SEARCH function
    sql = f"""
    SELECT {cols}
    FROM TABLE(
        SNOWFLAKE.CORTEX.SEARCH(
            '{service_name}',
            '{escaped_query}',
            {limit}
        )
    )
    """
    result = client.execute_query(sql)
    return json.dumps(result, default=str)
