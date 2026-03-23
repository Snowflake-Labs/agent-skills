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

{context}

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
        database: str | None = None,
        schema_name: str | None = None,
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

        # Build MCP server config — spawn as a separate stdio process
        import sys

        from snowflake_mcp_server.server import get_allowed_tools

        # Pass Snowflake credentials to MCP server subprocess
        snowflake_env = self.config.get_snowflake_env()
        if not snowflake_env.get("SNOWFLAKE_HOST"):
            logger.warning("No Snowflake credentials configured — MCP tools will fail")

        mcp_config: dict[str, Any] = {
            "command": sys.executable,
            "args": ["-m", "snowflake_mcp_server"],
        }
        if snowflake_env:
            mcp_config["env"] = snowflake_env

        allowed_tools = get_allowed_tools()

        # Build system prompt with skills and context
        skills_summary = get_skills_summary(self.config.enabled_skills or None)
        if database and schema_name:
            context = (
                f"IMPORTANT: The user has selected database '{database}' and schema '{schema_name}' "
                f"as their working context. All queries MUST be scoped to {database}.{schema_name} "
                f"unless the user explicitly asks about other databases or schemas. "
                f"Do NOT explore other databases or list all databases — only work within "
                f"{database}.{schema_name}."
            )
        else:
            context = ""
        system = SYSTEM_PROMPT.format(skills_summary=skills_summary, context=context)

        # Configure agent options
        def _log_stderr(line: str) -> None:
            logger.warning("CLI stderr: %s", line.rstrip())

        options = ClaudeAgentOptions(
            cwd=str(project_dir),
            allowed_tools=[*allowed_tools, "Read", "Write", "Edit", "Glob", "Grep", "Bash", "Skill"],
            permission_mode="bypassPermissions",
            resume=session_id,
            mcp_servers={"snowflake": mcp_config},
            system_prompt=system,
            setting_sources=["user", "project"],
            stderr=_log_stderr,
        )

        # Stream agent events
        try:
            async for event in query(prompt=message, options=options):
                parsed = _parse_agent_event(event)
                parsed["conversation_id"] = conversation_id
                logger.info("Agent event: type=%s class=%s", parsed.get("type"), type(event).__name__)

                # Track session ID for resumption
                sid = parsed.pop("session_id", None) or (
                    getattr(event, "session_id", None)
                )
                if sid:
                    self._sessions[conversation_id] = sid
                    parsed["session_id"] = sid

                # Handle multi-block AssistantMessages
                extras = parsed.pop("_extra_events", None)
                yield parsed
                if extras:
                    for extra in extras:
                        extra["conversation_id"] = conversation_id
                        yield extra

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
    """Convert a claude-agent-sdk event to a serializable dict.

    The SDK yields typed message objects (SystemMessage, AssistantMessage,
    ResultMessage) — not simple dicts. AssistantMessage.content is a list
    of content blocks (TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock).
    We flatten these into individual frontend events.
    """
    class_name = type(event).__name__

    if class_name == "SystemMessage":
        return {"type": "system", "content": ""}

    if class_name == "ResultMessage":
        result = getattr(event, "result", "")
        session_id = getattr(event, "session_id", None)
        return {
            "type": "result",
            "content": str(result) if result else "",
            **({"session_id": session_id} if session_id else {}),
        }

    if class_name == "AssistantMessage":
        # AssistantMessage.content is a list of content blocks.
        # Flatten into the first meaningful block for the frontend.
        content_blocks = getattr(event, "content", [])
        parsed_events = []
        for block in content_blocks:
            block_class = type(block).__name__
            if block_class == "TextBlock":
                parsed_events.append({
                    "type": "text",
                    "content": getattr(block, "text", ""),
                })
            elif block_class == "ThinkingBlock":
                parsed_events.append({
                    "type": "thinking",
                    "content": getattr(block, "thinking", ""),
                })
            elif block_class == "ToolUseBlock":
                parsed_events.append({
                    "type": "tool_use",
                    "content": "",
                    "tool_name": getattr(block, "name", ""),
                    "tool_input": json.dumps(
                        getattr(block, "input", {}), default=str
                    ),
                })
            elif block_class == "ToolResultBlock":
                block_content = getattr(block, "content", "")
                if isinstance(block_content, list):
                    texts = []
                    for c in block_content:
                        if isinstance(c, dict) and "text" in c:
                            texts.append(c["text"])
                        elif hasattr(c, "text"):
                            texts.append(c.text)
                    block_content = "\n".join(texts)
                parsed_events.append({
                    "type": "tool_result",
                    "content": str(block_content),
                })

        # Return first event; stash extras for caller to handle
        if not parsed_events:
            error = getattr(event, "error", None)
            if error:
                return {"type": "error", "content": str(error)}
            return {"type": "assistant", "content": str(content_blocks)}

        # If multiple blocks, return them joined as a single event.
        # For most messages there's just one text block.
        if len(parsed_events) == 1:
            return parsed_events[0]

        # Multiple blocks: return text blocks joined, yield others separately
        # Store extras in _extra_events for the caller
        first = parsed_events[0]
        first["_extra_events"] = parsed_events[1:]
        return first

    # Fallback for unknown event types
    return {"type": class_name.lower(), "content": str(event)}
