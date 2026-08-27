#!/usr/bin/env bash
# Full local verification suite (macOS / Linux).
# Windows: .\scripts\run_full_local_verification.ps1

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/venv/bin/python" ]]; then
  PYTHON="$ROOT/venv/bin/python"
elif [[ -x "$ROOT/venv/Scripts/python.exe" ]]; then
  PYTHON="$ROOT/venv/Scripts/python.exe"
else
  echo "venv not found." >&2
  exit 1
fi

run_step() {
  local label="$1"
  shift
  echo ""
  echo "=== $label ==="
  "$@"
}

run_step "Backend pytest (non-integration)" "$PYTHON" -m pytest tests -m "not integration" -q
run_step "Holdout evaluation" "$PYTHON" scripts/evaluate_holdouts.py
run_step "Answer comparison" "$PYTHON" scripts/evaluate_answer_comparison.py
run_step "Live verification" "$PYTHON" scripts/evaluate_live_verified_generation.py
run_step "Mixed holdout 120" "$PYTHON" scripts/evaluate_mixed_holdout.py
run_step "Ablations" "$PYTHON" scripts/evaluate_ablations.py
run_step "Role comparison" "$PYTHON" scripts/evaluate_role_comparison.py
run_step "Frontend lint" npm --prefix frontend run lint
run_step "Frontend unit tests" npm --prefix frontend run test
run_step "Frontend e2e (skipped unless PLAYWRIGHT_RUN_E2E=1)" npm --prefix frontend run test:e2e

echo ""
echo "All local verification steps passed."
