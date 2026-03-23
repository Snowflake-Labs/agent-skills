"""Configuration for the Snowflake Builder App server."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Mapping: connections.toml key → AppConfig field / env var name
_CONN_TOML_MAP = {
    "host": ("snowflake_host", "SNOWFLAKE_HOST"),
    "account": ("snowflake_account", "SNOWFLAKE_ACCOUNT"),
    "user": ("snowflake_user", "SNOWFLAKE_USER"),
    "password": ("snowflake_password", "SNOWFLAKE_PASSWORD"),
    "authenticator": ("snowflake_authenticator", "SNOWFLAKE_AUTHENTICATOR"),
    "role": ("snowflake_role", "SNOWFLAKE_ROLE"),
    "warehouse": ("snowflake_warehouse", "SNOWFLAKE_WAREHOUSE"),
    "database": ("snowflake_database", "SNOWFLAKE_DATABASE"),
    "schema": ("snowflake_schema", "SNOWFLAKE_SCHEMA"),
}


def _read_connections_toml(connection_name: str) -> dict[str, str]:
    """Read a named connection from ~/.snowflake/connections.toml.

    Returns a dict mapping AppConfig field names to values.
    """
    toml_path = Path.home() / ".snowflake" / "connections.toml"
    if not toml_path.exists():
        return {}

    try:
        import tomllib
    except ModuleNotFoundError:
        # Python < 3.11 fallback
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError:
            logger.warning("No TOML parser available; cannot read connections.toml")
            return {}

    try:
        data = tomllib.loads(toml_path.read_text())
    except Exception as e:
        logger.warning("Failed to parse connections.toml: %s", e)
        return {}

    conn = data.get(connection_name, {})
    if not conn:
        logger.warning("Connection '%s' not found in connections.toml", connection_name)
        return {}

    result: dict[str, str] = {}
    for toml_key, (field_name, _env_var) in _CONN_TOML_MAP.items():
        val = conn.get(toml_key)
        if val:
            result[field_name] = str(val)
    return result


@dataclass
class AppConfig:
    """Server configuration loaded from environment variables."""

    # Snowflake
    snowflake_host: str = ""
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_authenticator: str | None = None
    snowflake_role: str | None = None
    snowflake_warehouse: str | None = None
    snowflake_database: str | None = None
    snowflake_schema: str | None = None
    snowflake_connection_name: str = ""

    # Application
    projects_base_dir: str = "./projects"
    env: str = "development"

    # Claude Agent SDK
    anthropic_api_key: str = ""
    claude_stream_timeout: int = 3_600_000  # 1 hour in ms

    # Skills
    enabled_skills: list[str] = field(default_factory=list)
    skills_only_mode: bool = False

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load configuration from environment variables.

        If SNOWFLAKE_HOST / SNOWFLAKE_PASSWORD are not set but
        SNOWFLAKE_CONNECTION_NAME is, falls back to reading
        ~/.snowflake/connections.toml for that connection.
        """
        skills_str = os.environ.get("ENABLED_SKILLS", "")
        enabled = [s.strip() for s in skills_str.split(",") if s.strip()] if skills_str else []

        host = os.environ.get("SNOWFLAKE_HOST", "")
        password = os.environ.get("SNOWFLAKE_PASSWORD", "") or os.environ.get("SNOWFLAKE_PAT", "")
        connection_name = os.environ.get("SNOWFLAKE_CONNECTION_NAME", "")

        # Fall back to connections.toml when env vars are missing
        toml_values: dict[str, str] = {}
        if (not host or not password) and connection_name:
            logger.info("Loading Snowflake creds from connections.toml [%s]", connection_name)
            toml_values = _read_connections_toml(connection_name)

        def _get(env_var: str, field_name: str, default: str = "") -> str:
            """Env var first, then connections.toml, then default."""
            return os.environ.get(env_var, "") or toml_values.get(field_name, default)

        return cls(
            snowflake_host=_get("SNOWFLAKE_HOST", "snowflake_host"),
            snowflake_account=_get("SNOWFLAKE_ACCOUNT", "snowflake_account"),
            snowflake_user=_get("SNOWFLAKE_USER", "snowflake_user"),
            snowflake_password=(
                _get("SNOWFLAKE_PASSWORD", "snowflake_password")
                or _get("SNOWFLAKE_PAT", "snowflake_password")
            ),
            snowflake_authenticator=_get("SNOWFLAKE_AUTHENTICATOR", "snowflake_authenticator") or None,
            snowflake_role=_get("SNOWFLAKE_ROLE", "snowflake_role") or None,
            snowflake_warehouse=_get("SNOWFLAKE_WAREHOUSE", "snowflake_warehouse") or None,
            snowflake_database=_get("SNOWFLAKE_DATABASE", "snowflake_database") or None,
            snowflake_schema=_get("SNOWFLAKE_SCHEMA", "snowflake_schema") or None,
            snowflake_connection_name=connection_name,
            projects_base_dir=os.environ.get("PROJECTS_BASE_DIR", "./projects"),
            env=os.environ.get("ENV", "development"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            claude_stream_timeout=int(os.environ.get("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", "3600000")),
            enabled_skills=enabled,
            skills_only_mode=os.environ.get("SKILLS_ONLY_MODE", "false").lower() == "true",
        )

    def get_snowflake_env(self) -> dict[str, str]:
        """Return Snowflake credentials as env vars for subprocesses."""
        env: dict[str, str] = {}
        for _toml_key, (field_name, env_var) in _CONN_TOML_MAP.items():
            val = getattr(self, field_name, None)
            if val:
                env[env_var] = str(val)
        # Backward compat: auth.py reads SNOWFLAKE_PAT
        if self.snowflake_password and "SNOWFLAKE_PAT" not in env:
            env["SNOWFLAKE_PAT"] = self.snowflake_password
        return env

    @property
    def projects_path(self) -> Path:
        """Resolved projects directory path."""
        return Path(self.projects_base_dir).resolve()

    def get_base_url(self) -> str:
        """Return the Snowflake REST API base URL."""
        host = self.snowflake_host
        if not host:
            raise ValueError("SNOWFLAKE_HOST is required")

        bare = host.removeprefix("https://").removeprefix("http://").rstrip("/")

        # Replace underscores with hyphens in the account part for TLS.
        if ".snowflakecomputing.com" in bare:
            account_part, suffix = bare.split(".snowflakecomputing.com", 1)
            account_part = account_part.replace("_", "-")
            bare = f"{account_part}.snowflakecomputing.com{suffix}"

        return f"https://{bare}"

    def get_auth_headers(self) -> dict[str, str]:
        """Return authorization headers for Snowflake REST API calls."""
        if not self.snowflake_password:
            raise ValueError("SNOWFLAKE_PASSWORD (or SNOWFLAKE_PAT) is required")
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.snowflake_password}",
            "Content-Type": "application/json",
        }
        if not self.snowflake_authenticator or self.snowflake_authenticator.upper() not in ("OAUTH", "EXTERNALBROWSER"):
            headers["X-Snowflake-Authorization-Token-Type"] = "PROGRAMMATIC_ACCESS_TOKEN"
        return headers
