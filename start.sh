#!/usr/bin/env bash
# Everyday start: Docker + API + UI (macOS / Linux). Usage: ./start.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo ""
echo "========================================"
echo "  Trust-RAG — START"
echo "========================================"
echo ""

if [[ ! -x "$ROOT/venv/bin/python" ]]; then
  echo "ERROR: venv missing. Run ./setup.sh first."
  exit 1
fi
if [[ ! -f "$ROOT/.env" ]]; then
  echo "ERROR: .env missing. Run ./setup.sh first."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker is not running."
  exit 1
fi

export LOCAL_STACK=1
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"

port_in_use() {
  local port="$1"
  if command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$port" >/dev/null 2>&1
  else
    return 1
  fi
}

if [[ "$POSTGRES_PORT" == "5432" ]] && port_in_use 5432; then
  echo "Port 5432 in use — using 5433 for Postgres."
  export POSTGRES_PORT=5433
fi

echo "=== Starting Postgres + Qdrant ==="
docker compose up -d

DEMO_PASSWORD="$(grep -E '^BOOTSTRAP_USER_PASSWORD=' .env | head -1 | cut -d= -f2- || true)"
DEMO_PASSWORD="${DEMO_PASSWORD:-(see .env)}"

mkdir -p .run
echo "=== Starting backend (log: .run/backend.log) ==="
nohup "$ROOT/venv/bin/python" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload \
  >.run/backend.log 2>&1 &
echo $! >.run/backend.pid

echo "=== Starting frontend (log: .run/frontend.log) ==="
nohup npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 \
  >.run/frontend.log 2>&1 &
echo $! >.run/frontend.pid

echo ""
echo "========================================"
echo "  Started in background"
echo "========================================"
echo ""
echo "Wait ~15–30 seconds, then open:"
echo "  http://127.0.0.1:5173"
echo ""
echo "Login: harshini@company.com"
echo "Pass:  $DEMO_PASSWORD"
echo ""
echo "Logs:   tail -f .run/backend.log   /   .run/frontend.log"
echo "Stop:   ./stop.sh"
echo ""
