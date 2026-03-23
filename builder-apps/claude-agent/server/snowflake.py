"""Lightweight Snowflake SQL API client for metadata queries."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from server.config import AppConfig

logger = logging.getLogger(__name__)


async def run_sql(config: AppConfig, sql: str) -> list[dict[str, Any]]:
    """Execute a SQL statement via the Snowflake SQL API and return rows as dicts."""
    url = f"{config.get_base_url()}/api/v2/statements"

    body: dict[str, Any] = {"statement": sql, "timeout": 30}
    if config.snowflake_warehouse:
        body["warehouse"] = config.snowflake_warehouse.upper()
    if config.snowflake_role:
        body["role"] = config.snowflake_role.upper()

    async with httpx.AsyncClient(verify=True, timeout=30) as client:
        resp = await client.post(url, headers=config.get_auth_headers(), json=body)
        resp.raise_for_status()

    data = resp.json()
    columns = [col["name"] for col in data.get("resultSetMetaData", {}).get("rowType", [])]
    rows = data.get("data", [])
    return [dict(zip(columns, row)) for row in rows]


async def list_databases(config: AppConfig) -> list[dict[str, str | None]]:
    """Return databases the current role can access."""
    rows = await run_sql(config, "SHOW DATABASES")
    return [
        {"name": r.get("name", ""), "comment": r.get("comment") or None}
        for r in rows
    ]


async def list_schemas(config: AppConfig, database: str) -> list[dict[str, str | None]]:
    """Return schemas in a database the current role can access."""
    rows = await run_sql(config, f"SHOW SCHEMAS IN DATABASE \"{database}\"")
    return [
        {"name": r.get("name", ""), "comment": r.get("comment") or None}
        for r in rows
    ]
