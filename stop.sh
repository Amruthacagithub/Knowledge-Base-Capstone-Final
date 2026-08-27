#!/usr/bin/env bash
# Stop local Trust-RAG (macOS / Linux). Usage: ./stop.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== Stopping backend/frontend ==="
if [[ -f .run/backend.pid ]]; then
  kill "$(cat .run/backend.pid)" 2>/dev/null || true
  rm -f .run/backend.pid
fi
if [[ -f .run/frontend.pid ]]; then
  # npm often spawns children; kill process group if possible
  kill "$(cat .run/frontend.pid)" 2>/dev/null || true
  rm -f .run/frontend.pid
fi

# Free ports if still held
for port in 8000 5173; do
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [[ -n "${pids}" ]]; then
      echo "Killing leftover PIDs on $port: $pids"
      # shellcheck disable=SC2086
      kill $pids 2>/dev/null || true
    fi
  fi
done

echo "=== Stopping Docker services ==="
docker compose stop || true

echo ""
echo "Stopped. Run ./start.sh when you want the app again."
echo ""
