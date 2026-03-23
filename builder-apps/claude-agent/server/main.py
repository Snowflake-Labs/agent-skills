"""FastAPI backend for the Snowflake Builder App.

Provides REST + SSE endpoints for the React frontend to interact with
Claude Code agent sessions backed by Snowflake MCP tools.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from server.agent import AgentSessionManager
from server.config import AppConfig
from server.models import (
    AgentEvent,
    ConversationResponse,
    CreateProjectRequest,
    DatabaseInfo,
    InvokeAgentRequest,
    ProjectResponse,
    SchemaInfo,
)
from server.snowflake import list_databases, list_schemas

# Load .env.local for development
load_dotenv(".env.local")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize
config = AppConfig.from_env()
agent_manager = AgentSessionManager(config)

# Simple in-memory stores (replace with Snowflake tables for persistence)
_projects: dict[str, dict] = {}
_conversations: dict[str, dict] = {}

app = FastAPI(
    title="Snowflake Builder App",
    description="Claude Code agent interface with integrated Snowflake tools",
    version="0.1.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/databases")
async def get_databases() -> list[DatabaseInfo]:
    """List Snowflake databases the current role can access."""
    try:
        dbs = await list_databases(config)
    except Exception as e:
        logger.exception("Failed to list databases")
        raise HTTPException(status_code=500, detail=str(e))
    return [DatabaseInfo(name=d["name"], comment=d.get("comment")) for d in dbs]


@app.get("/api/databases/{database}/schemas")
async def get_schemas(database: str) -> list[SchemaInfo]:
    """List schemas in a Snowflake database."""
    try:
        schemas = await list_schemas(config, database)
    except Exception as e:
        logger.exception("Failed to list schemas for %s", database)
        raise HTTPException(status_code=500, detail=str(e))
    return [SchemaInfo(name=s["name"], comment=s.get("comment")) for s in schemas]


@app.post("/api/projects")
async def create_project(req: CreateProjectRequest) -> ProjectResponse:
    """Create a new project."""
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    project = {
        "id": project_id,
        "name": req.name,
        "description": req.description,
        "created_at": now,
    }
    _projects[project_id] = project

    # Create project directory
    project_dir = config.projects_path / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    return ProjectResponse(**project)


@app.get("/api/projects")
async def list_projects() -> list[ProjectResponse]:
    """List all projects."""
    return [ProjectResponse(**p) for p in _projects.values()]


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str) -> ProjectResponse:
    """Get a specific project."""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**_projects[project_id])


@app.get("/api/projects/{project_id}/conversations")
async def list_conversations(project_id: str) -> list[ConversationResponse]:
    """List conversations for a project."""
    convos = [
        ConversationResponse(**c)
        for c in _conversations.values()
        if c["project_id"] == project_id
    ]
    return sorted(convos, key=lambda c: c.updated_at, reverse=True)


@app.post("/api/invoke_agent")
async def invoke_agent(req: InvokeAgentRequest):
    """Invoke the Claude agent with Snowflake tools. Returns SSE stream."""
    now = datetime.now(timezone.utc).isoformat()

    # Ensure project exists
    if req.project_id not in _projects:
        _projects[req.project_id] = {
            "id": req.project_id,
            "name": "Default Project",
            "description": "",
            "created_at": now,
        }

    # Get or create conversation
    conversation_id = req.conversation_id
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        _conversations[conversation_id] = {
            "id": conversation_id,
            "project_id": req.project_id,
            "title": req.message[:50],
            "claude_session_id": None,
            "created_at": now,
            "updated_at": now,
        }

    message = req.message

    async def event_stream():
        async for event in agent_manager.invoke_agent(
            message=message,
            project_id=req.project_id,
            conversation_id=conversation_id,
            database=req.database,
            schema_name=req.schema_name,
        ):
            # Update conversation metadata
            if conversation_id in _conversations:
                _conversations[conversation_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
                if event.get("session_id"):
                    _conversations[conversation_id]["claude_session_id"] = event["session_id"]

            data = json.dumps(event, default=str)
            yield f"event: {event.get('type', 'message')}\ndata: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Serve React frontend in production
CLIENT_BUILD = Path(__file__).parent.parent / "client" / "dist"
if CLIENT_BUILD.exists():
    app.mount("/", StaticFiles(directory=str(CLIENT_BUILD), html=True))
