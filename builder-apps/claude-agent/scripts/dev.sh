#!/usr/bin/env bash
# Start both backend and frontend for development.
# Run from the builder-apps/claude-agent/ directory.

set -euo pipefail
cd "$(dirname "$0")/.."

# Start backend
echo "Starting FastAPI backend on :8000..."
uvicorn server.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "Starting React frontend on :5173..."
cd client
npm run dev &
FRONTEND_PID=$!
cd ..

# Cleanup on exit
cleanup() {
  echo ""
  echo "Shutting down..."
  kill $BACKEND_PID 2>/dev/null || true
  kill $FRONTEND_PID 2>/dev/null || true
}
trap cleanup EXIT

echo ""
echo "=== Snowflake Builder App ==="
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop."
wait
