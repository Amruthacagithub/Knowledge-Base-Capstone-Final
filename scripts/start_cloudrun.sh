#!/bin/sh
set -e
echo "=== Cloud Run startup: schema + optional ingest ==="
python scripts/init_db.py
if [ "${RUN_INGEST_ON_STARTUP:-false}" = "true" ]; then
  echo "=== Running full corpus ingest (slow; set RUN_INGEST_ON_STARTUP=false after first boot) ==="
  python scripts/ingest.py
fi
echo "=== Starting API on port ${PORT:-8080} ==="
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8080}"
