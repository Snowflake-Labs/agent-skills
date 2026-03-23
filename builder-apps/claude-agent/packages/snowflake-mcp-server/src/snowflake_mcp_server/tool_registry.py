"""Tool registry for the Snowflake MCP server.

Defines all available Snowflake tools with their schemas for claude-agent-sdk.
"""

from __future__ import annotations

from typing import Any, Callable

from snowflake_tools_core.tools import (
    catalog_tools,
    cortex_tools,
    pipeline_tools,
    sql_tools,
    stage_tools,
)


# Each tool definition: (function, description, input_schema)
TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "execute_sql": {
        "fn": sql_tools.execute_sql,
        "description": (
            "Execute a SQL query on Snowflake and return results. "
            "Use this for SELECT queries, DML, and DDL. "
            "Results are returned as JSON with columns, rows, and row_count."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The SQL query to execute."},
                "database": {"type": "string", "description": "Optional database context."},
                "schema": {"type": "string", "description": "Optional schema context."},
            },
            "required": ["query"],
        },
    },
    "execute_sql_multi": {
        "fn": sql_tools.execute_sql_multi,
        "description": "Execute multiple SQL statements in order and return all results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of SQL statements to execute sequentially.",
                },
            },
            "required": ["queries"],
        },
    },
    "list_databases": {
        "fn": catalog_tools.list_databases,
        "description": "List all databases accessible to the current role.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "list_schemas": {
        "fn": catalog_tools.list_schemas,
        "description": "List all schemas in a specific database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "database": {"type": "string", "description": "The database name."},
            },
            "required": ["database"],
        },
    },
    "list_tables": {
        "fn": catalog_tools.list_tables,
        "description": "List all tables and views in a database schema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "database": {"type": "string", "description": "The database name."},
                "schema": {"type": "string", "description": "The schema name."},
            },
            "required": ["database", "schema"],
        },
    },
    "describe_table": {
        "fn": catalog_tools.describe_table,
        "description": "Describe a table's columns, types, nullability, and comments.",
        "input_schema": {
            "type": "object",
            "properties": {
                "database": {"type": "string", "description": "The database name."},
                "schema": {"type": "string", "description": "The schema name."},
                "table": {"type": "string", "description": "The table name."},
            },
            "required": ["database", "schema", "table"],
        },
    },
    "get_ddl": {
        "fn": catalog_tools.get_ddl,
        "description": "Get the DDL (CREATE statement) for any Snowflake object.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_type": {
                    "type": "string",
                    "description": "Object type: TABLE, VIEW, FUNCTION, PROCEDURE, TASK, etc.",
                },
                "database": {"type": "string", "description": "The database name."},
                "schema": {"type": "string", "description": "The schema name."},
                "name": {"type": "string", "description": "The object name."},
            },
            "required": ["object_type", "database", "schema", "name"],
        },
    },
    "upload_to_stage": {
        "fn": stage_tools.upload_to_stage,
        "description": "Upload a local file to a Snowflake stage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "local_path": {"type": "string", "description": "Path to the local file."},
                "stage_path": {
                    "type": "string",
                    "description": "Target stage path (e.g., @my_stage/path/).",
                },
                "auto_compress": {"type": "boolean", "description": "Auto-compress the file.", "default": True},
            },
            "required": ["local_path", "stage_path"],
        },
    },
    "list_stage_files": {
        "fn": stage_tools.list_stage_files,
        "description": "List files in a Snowflake stage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stage_path": {"type": "string", "description": "Stage path (e.g., @my_stage)."},
                "pattern": {"type": "string", "description": "Optional file pattern to filter."},
            },
            "required": ["stage_path"],
        },
    },
    "list_tasks": {
        "fn": pipeline_tools.list_tasks,
        "description": "List Snowflake Tasks (scheduled SQL/stored procedure jobs).",
        "input_schema": {
            "type": "object",
            "properties": {
                "database": {"type": "string", "description": "Optional database scope."},
                "schema": {"type": "string", "description": "Optional schema scope."},
            },
        },
    },
    "list_dynamic_tables": {
        "fn": pipeline_tools.list_dynamic_tables,
        "description": "List Snowflake Dynamic Tables (declarative data pipelines).",
        "input_schema": {
            "type": "object",
            "properties": {
                "database": {"type": "string", "description": "Optional database scope."},
                "schema": {"type": "string", "description": "Optional schema scope."},
            },
        },
    },
    "cortex_complete": {
        "fn": cortex_tools.cortex_complete,
        "description": "Run a Snowflake Cortex AI completion (LLM inference).",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The text prompt."},
                "model": {
                    "type": "string",
                    "description": "Model name (default: claude-4-sonnet).",
                    "default": "claude-4-sonnet",
                },
            },
            "required": ["prompt"],
        },
    },
}


def get_all_tools() -> dict[str, dict[str, Any]]:
    """Return the full tool registry."""
    return TOOL_REGISTRY
