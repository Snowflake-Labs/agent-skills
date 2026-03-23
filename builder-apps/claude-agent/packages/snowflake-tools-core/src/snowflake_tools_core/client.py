"""Snowflake connector client wrapper.

Provides a thin wrapper around snowflake-connector-python for executing
queries and returning structured results.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Generator

import snowflake.connector

from snowflake_tools_core.auth import SnowflakeAuth, get_snowflake_auth


class SnowflakeClient:
    """Manages Snowflake connections and query execution."""

    def __init__(self, auth: SnowflakeAuth | None = None):
        self._auth = auth or get_snowflake_auth()

    @contextmanager
    def connection(self) -> Generator[snowflake.connector.SnowflakeConnection, None, None]:
        """Create a Snowflake connection using resolved auth."""
        connect_params: dict[str, Any] = {
            "account": self._auth.account,
            "host": self._auth.host,
        }

        if self._auth.user:
            connect_params["user"] = self._auth.user

        if self._auth.auth_type == "session_token":
            connect_params["token"] = self._auth.token
            connect_params["authenticator"] = "oauth"
        else:
            # PAT — pass as password and let the connector auto-detect
            connect_params["password"] = self._auth.token

        if self._auth.role:
            connect_params["role"] = self._auth.role
        if self._auth.warehouse:
            connect_params["warehouse"] = self._auth.warehouse
        if self._auth.database:
            connect_params["database"] = self._auth.database
        if self._auth.schema:
            connect_params["schema"] = self._auth.schema

        conn = snowflake.connector.connect(**connect_params)
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a SQL query and return results as a dict.

        Returns:
            {
                "columns": ["col1", "col2", ...],
                "rows": [[val1, val2, ...], ...],
                "row_count": int,
                "query_id": str
            }
        """
        with self.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(sql, params)
                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = cur.fetchall()
                # Convert non-serializable types
                clean_rows = []
                for row in rows:
                    clean_row = []
                    for val in row:
                        if isinstance(val, (bytes, bytearray)):
                            clean_row.append(val.hex())
                        elif hasattr(val, "isoformat"):
                            clean_row.append(val.isoformat())
                        else:
                            clean_row.append(val)
                    clean_rows.append(clean_row)

                return {
                    "columns": columns,
                    "rows": clean_rows,
                    "row_count": len(clean_rows),
                    "query_id": cur.sfqid or "",
                }
            finally:
                cur.close()

    def execute_multi(self, statements: list[str]) -> list[dict[str, Any]]:
        """Execute multiple SQL statements and return all results."""
        results = []
        for stmt in statements:
            stmt = stmt.strip()
            if stmt:
                results.append(self.execute_query(stmt))
        return results

    def execute_ddl(self, sql: str) -> dict[str, Any]:
        """Execute a DDL statement (CREATE, ALTER, DROP, etc.)."""
        with self.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(sql)
                # DDL returns status messages
                result = cur.fetchone()
                return {
                    "status": result[0] if result else "Success",
                    "query_id": cur.sfqid or "",
                }
            finally:
                cur.close()
