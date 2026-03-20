"""Pydantic models for API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class InvokeAgentRequest(BaseModel):
    """Request body for /api/invoke_agent."""

    message: str
    project_id: str
    conversation_id: str | None = None


class CreateProjectRequest(BaseModel):
    """Request body for /api/projects."""

    name: str
    description: str = ""


class ProjectResponse(BaseModel):
    """Response for a project."""

    id: str
    name: str
    description: str
    created_at: str


class ConversationResponse(BaseModel):
    """Response for a conversation."""

    id: str
    project_id: str
    title: str
    claude_session_id: str | None = None
    created_at: str
    updated_at: str


class AgentEvent(BaseModel):
    """SSE event from the agent stream."""

    type: str  # text, thinking, tool_use, tool_result, error, done
    content: str = ""
    tool_name: str | None = None
    tool_input: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
