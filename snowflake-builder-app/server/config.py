"""Configuration for the Snowflake Builder App server."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    """Server configuration loaded from environment variables."""

    # Snowflake
    snowflake_host: str = ""
    snowflake_account: str = ""
    snowflake_pat: str = ""
    snowflake_role: str | None = None
    snowflake_warehouse: str | None = None
    snowflake_database: str | None = None
    snowflake_schema: str | None = None

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
        """Load configuration from environment variables."""
        skills_str = os.environ.get("ENABLED_SKILLS", "")
        enabled = [s.strip() for s in skills_str.split(",") if s.strip()] if skills_str else []

        return cls(
            snowflake_host=os.environ.get("SNOWFLAKE_HOST", ""),
            snowflake_account=os.environ.get("SNOWFLAKE_ACCOUNT", ""),
            snowflake_pat=os.environ.get("SNOWFLAKE_PAT", ""),
            snowflake_role=os.environ.get("SNOWFLAKE_ROLE"),
            snowflake_warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
            snowflake_database=os.environ.get("SNOWFLAKE_DATABASE"),
            snowflake_schema=os.environ.get("SNOWFLAKE_SCHEMA"),
            projects_base_dir=os.environ.get("PROJECTS_BASE_DIR", "./projects"),
            env=os.environ.get("ENV", "development"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            claude_stream_timeout=int(os.environ.get("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", "3600000")),
            enabled_skills=enabled,
            skills_only_mode=os.environ.get("SKILLS_ONLY_MODE", "false").lower() == "true",
        )

    @property
    def projects_path(self) -> Path:
        """Resolved projects directory path."""
        return Path(self.projects_base_dir).resolve()
