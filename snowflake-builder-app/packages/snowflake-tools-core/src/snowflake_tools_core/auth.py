"""Snowflake authentication helpers.

Supports two auth modes:
- Local dev: PAT (Programmatic Access Token) from environment variables
- Container Runtime: Session token from /snowflake/session/token
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

CONTAINER_TOKEN_PATH = "/snowflake/session/token"


@dataclass
class SnowflakeAuth:
    """Resolved Snowflake authentication credentials."""

    account: str
    host: str
    token: str
    auth_type: str  # "pat" or "session_token"
    user: str | None = None
    role: str | None = None
    warehouse: str | None = None
    database: str | None = None
    schema: str | None = None


def _read_container_token() -> str | None:
    """Read session token from Container Runtime filesystem."""
    path = Path(CONTAINER_TOKEN_PATH)
    if path.exists():
        return path.read_text().strip()
    return None


def get_snowflake_auth() -> SnowflakeAuth:
    """Resolve Snowflake auth from environment or container runtime.

    Priority:
    1. Container Runtime token (/snowflake/session/token)
    2. Environment variables (SNOWFLAKE_PAT, SNOWFLAKE_HOST, etc.)

    Required env vars for local dev:
        SNOWFLAKE_HOST - Account URL (e.g., myaccount.snowflakecomputing.com)
        SNOWFLAKE_ACCOUNT - Account identifier
        SNOWFLAKE_PAT - Programmatic Access Token

    Optional env vars:
        SNOWFLAKE_USER - Username
        SNOWFLAKE_ROLE - Role to use
        SNOWFLAKE_WAREHOUSE - Warehouse to use
        SNOWFLAKE_DATABASE - Default database
        SNOWFLAKE_SCHEMA - Default schema
    """
    container_token = _read_container_token()

    if container_token:
        # Container Runtime — account/host come from Snowflake env
        return SnowflakeAuth(
            account=os.environ.get("SNOWFLAKE_ACCOUNT", ""),
            host=os.environ.get("SNOWFLAKE_HOST", ""),
            token=container_token,
            auth_type="session_token",
            user=os.environ.get("SNOWFLAKE_USER"),
            role=os.environ.get("SNOWFLAKE_ROLE"),
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
            database=os.environ.get("SNOWFLAKE_DATABASE"),
            schema=os.environ.get("SNOWFLAKE_SCHEMA"),
        )

    # Local dev — PAT from environment
    host = os.environ.get("SNOWFLAKE_HOST", "")
    account = os.environ.get("SNOWFLAKE_ACCOUNT", "")
    pat = os.environ.get("SNOWFLAKE_PAT", "")

    if not host or not pat:
        raise RuntimeError(
            "Snowflake auth not configured. Set SNOWFLAKE_HOST and SNOWFLAKE_PAT "
            "environment variables, or run inside Container Runtime."
        )

    return SnowflakeAuth(
        account=account,
        host=host,
        token=pat,
        auth_type="pat",
        user=os.environ.get("SNOWFLAKE_USER"),
        role=os.environ.get("SNOWFLAKE_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        database=os.environ.get("SNOWFLAKE_DATABASE"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA"),
    )


def get_auth_header(auth: SnowflakeAuth) -> dict[str, str]:
    """Build HTTP Authorization header for Snowflake REST APIs."""
    if auth.auth_type == "session_token":
        return {"Authorization": f'Snowflake Token="{auth.token}"'}
    return {"Authorization": f"Bearer {auth.token}"}
