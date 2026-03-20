"""Stage file operations for Snowflake."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from snowflake_tools_core.client import SnowflakeClient


def upload_to_stage(
    local_path: str,
    stage_path: str,
    auto_compress: bool = True,
) -> str:
    """Upload a local file to a Snowflake stage.

    Args:
        local_path: Path to the local file.
        stage_path: Target stage path (e.g., @my_stage/path/).
        auto_compress: Whether to auto-compress the file (default: True).

    Returns:
        JSON string with upload status.
    """
    client = SnowflakeClient()
    compress = "AUTO_COMPRESS=TRUE" if auto_compress else "AUTO_COMPRESS=FALSE"
    sql = f"PUT 'file://{local_path}' '{stage_path}' {compress} OVERWRITE=TRUE"
    result = client.execute_query(sql)
    return json.dumps({
        "status": "uploaded",
        "source": local_path,
        "target": stage_path,
        "details": result,
    }, default=str)


def list_stage_files(stage_path: str, pattern: str | None = None) -> str:
    """List files in a Snowflake stage.

    Args:
        stage_path: Stage path (e.g., @my_stage or @my_stage/subdir/).
        pattern: Optional file pattern to filter results.

    Returns:
        JSON string with file names, sizes, and last modified dates.
    """
    client = SnowflakeClient()
    sql = f"LIST {stage_path}"
    if pattern:
        sql += f" PATTERN='{pattern}'"

    result = client.execute_query(sql)
    files = [
        {
            "name": row[0],
            "size": row[1],
            "md5": row[2] if len(row) > 2 else None,
            "last_modified": str(row[3]) if len(row) > 3 else None,
        }
        for row in result["rows"]
    ]
    return json.dumps({"files": files, "count": len(files), "stage": stage_path}, default=str)
