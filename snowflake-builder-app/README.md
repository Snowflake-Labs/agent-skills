# Snowflake Builder App

A web application that provides a Claude Code agent interface with integrated Snowflake tools. Users interact with Claude through a chat interface, and the agent can execute SQL queries, explore schemas, manage pipelines, upload files, and more on their Snowflake workspace.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Web Application                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  React Frontend (client/)           FastAPI Backend (server/)               │
│  ┌─────────────────────┐            ┌─────────────────────────────────┐     │
│  │ Chat UI             │◄──────────►│ /api/invoke_agent               │     │
│  │ Project Selector    │   SSE      │ /api/projects                   │     │
│  │ Conversation List   │            │ /api/conversations              │     │
│  └─────────────────────┘            └─────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Claude Code Session                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Each user message spawns a Claude Code agent session via claude-agent-sdk  │
│                                                                             │
│  Built-in Tools:              MCP Tools (Snowflake):       Skills:          │
│  ┌──────────────────┐         ┌──────────────────────┐    ┌───────────┐    │
│  │ Read, Write, Edit│         │ execute_sql          │    │ snowpipe  │    │
│  │ Glob, Grep, Skill│         │ list_databases       │    │ docker    │    │
│  └──────────────────┘         │ describe_table       │    │ drizzle   │    │
│                               │ upload_to_stage      │    │ ...       │    │
│                               │ list_tasks           │    └───────────┘    │
│                               │ cortex_complete      │                     │
│                               └──────────────────────┘                     │
│                                          │                                 │
│                                          ▼                                 │
│                               ┌──────────────────────┐                     │
│                               │ snowflake-mcp-server  │                    │
│                               │ (in-process SDK tools)│                    │
│                               └──────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Snowflake Workspace                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Warehouses  │  Databases/Schemas  │  Stages  │  Tasks  │  Cortex AI       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## How It Works

### 1. Claude Code Sessions

When a user sends a message, the backend creates a Claude Code session using the `claude-agent-sdk`:

```python
from claude_agent_sdk import ClaudeAgentOptions, query

options = ClaudeAgentOptions(
    cwd=str(project_dir),
    allowed_tools=[*snowflake_tools, "Read", "Write", "Edit", "Glob", "Grep"],
    permission_mode="bypassPermissions",
    resume=session_id,
    mcp_servers={"snowflake": snowflake_mcp_server},
    system_prompt=system_prompt,
)

async for msg in query(prompt=message, options=options):
    yield msg  # Stream to frontend via SSE
```

Key features:
- **Session Resumption**: Each conversation stores a `claude_session_id` for context continuity
- **Streaming**: All events (text, thinking, tool_use, tool_result) stream to the frontend
- **Project Isolation**: Each project has its own working directory

### 2. Authentication Flow

```
Production (Container Runtime)          Development (Local)
┌──────────────────────────┐            ┌──────────────────────────┐
│ /snowflake/session/token │            │ SNOWFLAKE_PAT env var    │
└─────────────┬────────────┘            └─────────────┬────────────┘
              └──────────────┬────────────────────────┘
                             ▼
              ┌──────────────────────────┐
              │ get_snowflake_auth()     │
              │ - auto-detects mode      │
              │ - returns SnowflakeAuth  │
              └──────────────────────────┘
```

### 3. MCP Tools (Snowflake)

Tools exposed as `mcp__snowflake__<tool_name>`:

| Tool | Description |
|------|-------------|
| `execute_sql` | Execute SQL queries and DDL |
| `execute_sql_multi` | Execute multiple statements |
| `list_databases` | List accessible databases |
| `list_schemas` | List schemas in a database |
| `list_tables` | List tables and views in a schema |
| `describe_table` | Describe columns, types, comments |
| `get_ddl` | Get CREATE statement for any object |
| `upload_to_stage` | Upload files to Snowflake stages |
| `list_stage_files` | List files in a stage |
| `list_tasks` | List Snowflake Tasks |
| `list_dynamic_tables` | List Dynamic Tables |
| `cortex_complete` | Run Cortex AI completion |

### 4. Skills

Skills from `snowflake-skills/` are automatically copied into each project's `.claude/skills/` directory. The agent loads them via the Skill tool.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Snowflake account with:
  - Programmatic Access Token (PAT) or Container Runtime access
  - A warehouse for SQL execution
- Anthropic API key (for Claude Code sessions)

## Quick Start

### 1. Run the setup script

```bash
cd snowflake-builder-app
./scripts/setup.sh
```

### 2. Configure credentials

Edit `.env.local` with your Snowflake and Anthropic credentials:

```env
SNOWFLAKE_HOST=myaccount.snowflakecomputing.com
SNOWFLAKE_ACCOUNT=myaccount
SNOWFLAKE_PAT=pat_...
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Start the app

```bash
./scripts/dev.sh
```

Open http://localhost:5173 and start building.

## Project Structure

```
snowflake-builder-app/
├── client/                          # React frontend (Vite + TypeScript)
│   ├── src/
│   │   ├── App.tsx                  # Main app with chat + sidebar
│   │   ├── components/              # ChatInput, ChatMessage, etc.
│   │   ├── hooks/useSSEStream.ts    # SSE streaming hook
│   │   ├── services/api.ts          # API client
│   │   └── types/agent.ts           # TypeScript types
│   └── package.json
├── server/                          # FastAPI backend
│   ├── main.py                      # FastAPI app, CORS, endpoints
│   ├── agent.py                     # Claude agent session management
│   ├── config.py                    # Environment config
│   ├── models.py                    # Pydantic models
│   └── skills.py                    # Skills loader
├── packages/
│   ├── snowflake-tools-core/        # Snowflake tool implementations
│   │   └── src/snowflake_tools_core/
│   │       ├── auth.py              # PAT + session token auth
│   │       ├── client.py            # Snowflake connector wrapper
│   │       └── tools/               # SQL, catalog, stage, pipeline, cortex
│   └── snowflake-mcp-server/        # MCP server wrapping tools
│       └── src/snowflake_mcp_server/
│           ├── server.py            # MCP server factory
│           └── tool_registry.py     # Tool definitions + schemas
├── scripts/
│   ├── setup.sh                     # One-click setup
│   └── dev.sh                       # Start frontend + backend
├── .env.example                     # Config template
├── pyproject.toml
├── requirements.txt
└── README.md
```
