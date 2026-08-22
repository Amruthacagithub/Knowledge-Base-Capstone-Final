#!/usr/bin/env bash
# Start and verify the local Trust-RAG stack (CPU-only, no Gemini required).
# Usage: ./scripts/run_local_trust_stack.sh
# Works on macOS and Linux. Windows users: prefer run_local_trust_stack.ps1
# Requires: Docker, Python venv, .env with BOOTSTRAP_USER_PASSWORD set.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/venv/bin/python" ]]; then
  PYTHON="$ROOT/venv/bin/python"
elif [[ -x "$ROOT/venv/Scripts/python.exe" ]]; then
  PYTHON="$ROOT/venv/Scripts/python.exe"
else
  echo "venv not found. Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -f "$ROOT/.env" ]]; then
  echo ".env not found. Copy .env.example to .env and set BOOTSTRAP_USER_PASSWORD." >&2
  exit 1
fi

# .env may point at cloud services; local Docker stack must use localhost.
echo "=== Forcing local stack (LOCAL_STACK=1) ==="
export LOCAL_STACK=1

# If host port 5432 is already taken, use 5433 for this project's Postgres.
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
port_in_use() {
  local port="$1"
  if command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$port" >/dev/null 2>&1
  elif [[ -e /dev/tcp/127.0.0.1/$port ]]; then
    (echo >/dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1
  else
    return 1
  fi
}

if [[ "$POSTGRES_PORT" == "5432" ]] && port_in_use 5432; then
  echo "Port 5432 is in use; using POSTGRES_PORT=5433 for docker compose."
  export POSTGRES_PORT=5433
fi

echo "=== Starting Docker services ==="
docker compose up -d

echo "=== Initializing database ==="
"$PYTHON" scripts/init_db.py

echo "=== Building PDF corpus (if needed) ==="
"$PYTHON" scripts/build_pdf_corpus.py

echo "=== Ingesting documents ==="
"$PYTHON" scripts/ingest.py

echo "=== Checking CPU runtime ==="
"$PYTHON" scripts/check_cpu_runtime.py

echo ""
echo "=== Stack ready ==="
echo "Start backend:  $PYTHON -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
echo "Start frontend: npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173"
echo ""
echo "Smoke test (after backend is running):"
echo '  export SMOKE_API_PASSWORD="your-bootstrap-password"'
echo '  export SMOKE_TRUST_CHECKS=true'
echo "  $PYTHON scripts/smoke_api.py"
echo "  unset SMOKE_API_PASSWORD SMOKE_TRUST_CHECKS"
