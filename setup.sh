#!/usr/bin/env bash
# First-time local setup (macOS / Linux). Usage: ./setup.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo ""
echo "========================================"
echo "  Trust-RAG — first-time SETUP"
echo "========================================"
echo ""

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: '$1' not found. Install it, then re-run ./setup.sh"
    exit 1
  }
}

need python3
need npm
need docker

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker is not running. Start Docker, then re-run ./setup.sh"
  exit 1
fi

if [[ ! -x "$ROOT/venv/bin/python" ]]; then
  echo "=== Creating Python venv ==="
  python3 -m venv venv
fi
PY="$ROOT/venv/bin/python"

echo "=== Installing PyTorch (CPU) ==="
"$PY" -m pip install --upgrade pip
"$PY" -m pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
echo "=== Installing Python requirements ==="
"$PY" -m pip install -r requirements.txt

DEMO_PASSWORD="TrustDemo2026"
if [[ ! -f "$ROOT/.env" ]]; then
  echo "=== Creating .env from .env.example ==="
  cp .env.example .env
  if command -v sed >/dev/null 2>&1; then
    sed -i.bak "s/BOOTSTRAP_USER_PASSWORD=choose-an-initial-user-password/BOOTSTRAP_USER_PASSWORD=${DEMO_PASSWORD}/" .env
    rm -f .env.bak
  fi
  echo "Demo login password set to: $DEMO_PASSWORD"
else
  echo "=== .env already exists (left unchanged) ==="
  DEMO_PASSWORD="$(grep -E '^BOOTSTRAP_USER_PASSWORD=' .env | head -1 | cut -d= -f2- || true)"
  DEMO_PASSWORD="${DEMO_PASSWORD:-TrustDemo2026}"
fi

echo "=== Installing frontend npm packages ==="
npm --prefix frontend install

echo "=== Docker + database + ingest (can take several minutes) ==="
export LOCAL_STACK=1
export BOOTSTRAP_USER_PASSWORD="$DEMO_PASSWORD"
chmod +x scripts/*.sh
./scripts/run_local_trust_stack.sh

echo ""
echo "========================================"
echo "  SETUP COMPLETE"
echo "========================================"
echo ""
echo "Next:  ./start.sh"
echo "Then open  http://127.0.0.1:5173"
echo "Login: harshini@company.com"
echo "Pass:  $DEMO_PASSWORD"
echo ""
echo "You only need ./setup.sh once (or after big dependency updates)."
echo ""
