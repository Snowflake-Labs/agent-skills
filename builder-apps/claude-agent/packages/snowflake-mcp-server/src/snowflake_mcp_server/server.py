"""Snowflake MCP server for Claude Code agent integration.

Runs as a stdio MCP server process, exposing Snowflake tools via the
Model Context Protocol. Designed to be launched by claude-agent-sdk as:

    python -m snowflake_mcp_server
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import Any, Optional

from fastmcp import FastMCP

from snowflake_mcp_server.tool_registry import get_all_tools

logger = logging.getLogger(__name__)


def create_stdio_server() -> FastMCP:
    """Build a FastMCP server with all Snowflake tools registered."""
    server = FastMCP("snowflake")

    registry = get_all_tools()
    for tool_name, tool_def in registry.items():
        _register_tool(server, tool_name, tool_def)

    return server


def _py_type(json_type: str):
    """Map JSON schema type to Python type annotation."""
    return {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }.get(json_type, str)


def _register_tool(
    server: FastMCP,
    name: str,
    tool_def: dict[str, Any],
) -> None:
    """Register a single tool from the registry onto the FastMCP server."""
    fn = tool_def["fn"]
    description = tool_def["description"]
    schema = tool_def["input_schema"]
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    # Build an explicit signature FastMCP can parse (no **kwargs).
    params = []
    annotations: dict[str, Any] = {}
    for p_name, p_info in props.items():
        py_type = _py_type(p_info.get("type", "string"))
        if p_name in required:
            params.append(
                inspect.Parameter(p_name, inspect.Parameter.KEYWORD_ONLY, annotation=py_type)
            )
        else:
            params.append(
                inspect.Parameter(
                    p_name,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=None,
                    annotation=Optional[py_type],
                )
            )
        annotations[p_name] = params[-1].annotation
    annotations["return"] = str
    sig = inspect.Signature(params, return_annotation=str)

    # Build the handler with its own closure over fn/props
    def _make_handler(_fn=fn, _props=props):
        async def handler(**kwargs: Any) -> str:
            try:
                filtered = {k: v for k, v in kwargs.items() if k in _props and v is not None}
                result = _fn(**filtered)
                if isinstance(result, str):
                    return result
                return json.dumps(result, default=str)
            except Exception as e:
                logger.exception(f"Tool execution failed: {_fn.__name__}")
                return json.dumps({"error": str(e)})

        handler.__name__ = name
        handler.__qualname__ = name
        handler.__doc__ = description
        handler.__signature__ = sig
        handler.__annotations__ = annotations
        return handler

    server.add_tool(_make_handler())


def get_allowed_tools(prefix: str = "mcp__snowflake") -> list[str]:
    """Get the list of allowed tool names with MCP prefix.

    Returns:
        List like ['mcp__snowflake__execute_sql', 'mcp__snowflake__list_databases', ...]
    """
    registry = get_all_tools()
    return [f"{prefix}__{name}" for name in registry.keys()]
