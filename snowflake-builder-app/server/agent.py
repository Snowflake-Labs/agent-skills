"""Claude agent session management for the Snowflake Builder App.

Handles creating and running Claude Code sessions with Snowflake MCP tools.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator

from server.config import AppConfig
from server.skills import copy_skills_to_project, get_skills_summary

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert Snowflake developer assistant. You help users build, query, \
and manage their Snowflake data platform through natural conversation.

You have access to Snowflake tools that let you:
- Execute SQL queries and DDL statements
- Browse databases, schemas, and tables
- Upload files to stages
- Manage Tasks and Dynamic Tables
- Use Cortex AI for completions

When a user asks you to do something on Snowflake, use the appropriate tool. \
Always confirm destructive operations (DROP, DELETE, TRUNCATE) before executing.

When writing SQL, prefer Snowflake-specific syntax and features. Use fully-qualified \
object names (database.schema.object) when possible.

{skills_summary}
"""


class AgentSessionManager:
    """Manages Claude Code agent sessions with Snowflake tools."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._sessions: dict[str, str] = {}  # conversation_id -> claude_session_id

    def _get_project_dir(self, project_id: str) -> Path:
        """Get or create the project working directory."""
        project_dir = self.config.projects_path / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def _ensure_skills(self, project_dir: Path) -> None:
        """Ensure skills are copied to the project directory."""
        skills_dir = project_dir / ".claude" / "skills"
        if not skills_dir.exists():
            copy_skills_to_project(project_dir, self.config.enabled_skills or None)

    async def invoke_agent(
        self,
        message: str,
        project_id: str,
        conversation_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Invoke the Claude agent and stream events.

        Args:
            message: User message to send to the agent.
            project_id: Project context for the conversation.
            conversation_id: Optional conversation ID to resume.

        Yields:
            Event dicts with type, content, and metadata.
        """
        try:
            from claude_agent_sdk import ClaudeAgentOptions, query
        except ImportError:
            yield {
                "type": "error",
                "content": (
                    "claude-agent-sdk is not installed. "
                    "Install it with: pip install claude-agent-sdk"
                ),
            }
            return

        # Set up project directory and skills
        project_dir = self._get_project_dir(project_id)
        self._ensure_skills(project_dir)

        # Resolve conversation session
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        session_id = self._sessions.get(conversation_id)

        # Build MCP server config for Snowflake tools
        from snowflake_mcp_server.server import create_mcp_server, get_allowed_tools

        mcp_config = create_mcp_server("snowflake")
        allowed_tools = get_allowed_tools()

        # Build system prompt with skills
        skills_summary = get_skills_summary(self.config.enabled_skills or None)
        system = SYSTEM_PROMPT.format(skills_summary=skills_summary)

        # Configure agent options
        options = ClaudeAgentOptions(
            cwd=str(project_dir),
            allowed_tools=[*allowed_tools, "Read", "Write", "Edit", "Glob", "Grep", "Bash", "Skill"],
            permission_mode="bypassPermissions",
            resume=session_id,
            mcp_servers={"snowflake": mcp_config},
            system_prompt=system,
            setting_sources=["user", "project"],
        )

        # Stream agent events
        try:
            async for event in query(prompt=message, options=options):
                event_type = getattr(event, "type", "unknown")
                parsed = _parse_agent_event(event)
                parsed["conversation_id"] = conversation_id

                # Track session ID for resumption
                if hasattr(event, "session_id") and event.session_id:
                    self._sessions[conversation_id] = event.session_id
                    parsed["session_id"] = event.session_id

                yield parsed

        except Exception as e:
            logger.exception("Agent invocation failed")
            yield {
                "type": "error",
                "content": f"Agent error: {str(e)}",
                "conversation_id": conversation_id,
            }

        # Signal completion
        yield {
            "type": "done",
            "content": "",
            "conversation_id": conversation_id,
        }


def _parse_agent_event(event: Any) -> dict[str, Any]:
    """Convert a claude-agent-sdk event to a serializable dict."""
    event_type = getattr(event, "type", "unknown")

    if event_type == "text":
        return {"type": "text", "content": getattr(event, "text", "")}
    elif event_type == "thinking":
        return {"type": "thinking", "content": getattr(event, "text", "")}
    elif event_type == "tool_use":
        return {
            "type": "tool_use",
            "content": "",
            "tool_name": getattr(event, "name", ""),
            "tool_input": json.dumps(getattr(event, "input", {}), default=str),
        }
    elif event_type == "tool_result":
        content = getattr(event, "content", "")
        if isinstance(content, list):
            # Extract text from content blocks
            texts = [c.get("text", "") for c in content if isinstance(c, dict) and "text" in c]
            content = "\n".join(texts)
        return {"type": "tool_result", "content": str(content)}
    elif event_type == "error":
        return {"type": "error", "content": getattr(event, "message", str(event))}
    else:
        return {"type": event_type, "content": str(event)}
