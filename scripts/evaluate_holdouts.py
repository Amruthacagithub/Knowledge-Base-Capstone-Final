"""Evaluate frozen agent-reviewed holdout datasets."""
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "holdout-evaluation-only-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.evaluate_claim_verification import evaluate as evaluate_claims
from scripts.evaluate_evidence_extraction import evaluate as evaluate_extraction
from scripts.evaluate_query_planner import evaluate as evaluate_planner


ROOT = Path(__file__).resolve().parent.parent
EXTRACTION_HOLDOUT = ROOT / "evaluation" / "evidence_extraction_holdout_v1.json"
CLAIM_HOLDOUT = ROOT / "evaluation" / "claim_verification_holdout_v1.json"
PLANNER_HOLDOUT = ROOT / "evaluation" / "planner_routes_holdout_v1.json"

THRESHOLDS = {
    "extraction_entity_f1": 0.85,
    "extraction_claim_f1": 0.80,
    "claim_macro_f1": 0.85,
    "planner_accuracy": 0.88,
    "planner_macro_f1": 0.85,
}


def evaluate() -> dict:
    extraction = evaluate_extraction(EXTRACTION_HOLDOUT)
    claims = evaluate_claims(CLAIM_HOLDOUT)
    planner = evaluate_planner(PLANNER_HOLDOUT)
    return {
        "scope": "agent-reviewed frozen holdouts; not independent human IRB review",
        "datasets": {
            "extraction": extraction["sha256"],
            "claims": claims["sha256"],
            "planner": planner["sha256"],
        },
        "extraction": {
            "entity_f1": extraction["metrics"]["entities"]["f1"],
            "relationship_f1": extraction["metrics"]["relationships"]["f1"],
            "claim_f1": extraction["metrics"]["claims"]["f1"],
            "failures": extraction["failures"],
        },
        "claims": {
            "accuracy": claims["accuracy"],
            "macro_f1": claims["macro_f1"],
            "failures": claims["failures"],
        },
        "planner": {
            "accuracy": planner["accuracy"],
            "macro_f1": planner["macro_f1"],
            "failures": planner["failures"],
        },
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    failures = []
    if result["extraction"]["entity_f1"] < THRESHOLDS["extraction_entity_f1"]:
        failures.append("extraction_entity_f1")
    if result["extraction"]["claim_f1"] < THRESHOLDS["extraction_claim_f1"]:
        failures.append("extraction_claim_f1")
    if result["claims"]["macro_f1"] < THRESHOLDS["claim_macro_f1"]:
        failures.append("claim_macro_f1")
    if result["planner"]["accuracy"] < THRESHOLDS["planner_accuracy"]:
        failures.append("planner_accuracy")
    if result["planner"]["macro_f1"] < THRESHOLDS["planner_macro_f1"]:
        failures.append("planner_macro_f1")
    if failures:
        print(f"FAIL: holdout thresholds not met for {', '.join(failures)}")
        return 1
    print("PASS: all holdout thresholds met.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
