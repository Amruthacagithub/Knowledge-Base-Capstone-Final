#!/bin/sh
set -e
echo "=== Cloud Run startup: schema + search index ==="
python scripts/init_db.py
python scripts/ensure_search_index.py
echo "=== Starting API on port ${PORT:-8080} ==="
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8080}"
