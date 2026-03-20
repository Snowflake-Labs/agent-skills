"""Snowflake MCP server for Claude Code agent integration.

Exposes Snowflake tools as MCP tools that can be loaded by claude-agent-sdk.
Tools are prefixed as mcp__snowflake__<tool_name>.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from snowflake_mcp_server.tool_registry import get_all_tools

logger = logging.getLogger(__name__)


def create_mcp_server(name: str = "snowflake") -> dict[str, Any]:
    """Create an MCP server config for claude-agent-sdk.

    This returns the configuration dict that can be passed to
    ClaudeAgentOptions(mcp_servers={...}).

    For in-process usage with claude-agent-sdk's create_sdk_mcp_server:
        from claude_agent_sdk import create_sdk_mcp_server
        server = create_sdk_mcp_server(name='snowflake', tools=get_sdk_tools())

    Returns:
        MCP server configuration dict.
    """
    return {
        "name": name,
        "tools": get_sdk_tools(),
    }


def get_sdk_tools() -> list[dict[str, Any]]:
    """Convert tool registry to claude-agent-sdk compatible tool definitions.

    Returns:
        List of tool dicts with name, description, input_schema, and handler.
    """
    registry = get_all_tools()
    tools = []

    for tool_name, tool_def in registry.items():
        tools.append({
            "name": tool_name,
            "description": tool_def["description"],
            "input_schema": tool_def["input_schema"],
            "handler": _make_handler(tool_def["fn"], tool_def["input_schema"]),
        })

    return tools


def _make_handler(fn, schema: dict[str, Any]):
    """Create a handler function that maps MCP input to tool function args."""

    def handler(input_data: dict[str, Any]) -> str:
        try:
            # Extract required and optional params from schema
            props = schema.get("properties", {})
            kwargs = {}
            for param_name in props:
                if param_name in input_data:
                    kwargs[param_name] = input_data[param_name]

            result = fn(**kwargs)
            if isinstance(result, str):
                return result
            return json.dumps(result, default=str)
        except Exception as e:
            logger.exception(f"Tool execution failed: {fn.__name__}")
            return json.dumps({"error": str(e)})

    return handler


def get_allowed_tools(prefix: str = "mcp__snowflake") -> list[str]:
    """Get the list of allowed tool names with MCP prefix.

    Returns:
        List like ['mcp__snowflake__execute_sql', 'mcp__snowflake__list_databases', ...]
    """
    registry = get_all_tools()
    return [f"{prefix}__{name}" for name in registry.keys()]
