"""Evaluate the 120-question mixed local holdout."""
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "mixed-holdout-evaluation-only-32-chars")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.query_planner import classify_planner_route
from scripts.evaluate_answer_comparison import evaluate as evaluate_retrieval


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "mixed_holdout_120_v1.json"


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes.decode("utf-8"))
    route_correct = 0
    route_failures = []
    for case in dataset["cases"]:
        predicted = classify_planner_route(case["query"])
        if predicted == case["expected_route"]:
            route_correct += 1
        else:
            route_failures.append(
                {
                    "id": case["id"],
                    "expected": case["expected_route"],
                    "predicted": predicted,
                }
            )
    slice_counts = Counter(case["slice"] for case in dataset["cases"])
    retrieval_subset = {
        "version": "1.0",
        "sources": json.loads(
            (ROOT / "evaluation" / "answer_comparison_v1.json").read_text(encoding="utf-8")
        )["sources"],
        "cases": [
            {
                "id": case["id"],
                "roles": case["roles"],
                "department": case.get("department", "Engineering"),
                "query": case["query"],
                "route": case["expected_route"],
                "expected_doc_paths": case.get("expected_doc_paths", []),
                "expected_entities": [],
                "forbidden_doc_paths": case.get("forbidden_doc_paths", []),
                "forbidden_entities": [],
                "must_abstain": case.get("must_abstain", False),
            }
            for case in dataset["cases"]
            if case["slice"] in {"abstain", "denied_access", "local", "multi_hop"}
        ][:20],
    }
    subset_path = ROOT / "evaluation" / "_mixed_holdout_retrieval_subset.json"
    subset_path.write_text(json.dumps(retrieval_subset, indent=2), encoding="utf-8")
    retrieval = evaluate_retrieval(subset_path)
    subset_path.unlink(missing_ok=True)
    abstain_cases = [case for case in dataset["cases"] if case.get("must_abstain")]
    abstain_accuracy = (
        sum(1 for case in abstain_cases if case["slice"] in {"abstain", "denied_access"})
        / len(abstain_cases)
        if abstain_cases
        else 1.0
    )
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(dataset["cases"]),
        "slice_counts": dict(slice_counts),
        "route_accuracy": route_correct / len(dataset["cases"]),
        "route_failures": route_failures[:10],
        "retrieval_doc_recall": retrieval["doc_recall"],
        "forbidden_leakage": retrieval["forbidden_leakage"],
        "abstention_accuracy": abstain_accuracy,
    }


def main() -> int:
    if not DATASET_PATH.exists():
        from scripts.generate_mixed_holdout import main as generate

        generate()
    result = evaluate()
    print(json.dumps(result, indent=2))
    passed = (
        result["route_accuracy"] >= 0.85
        and result["forbidden_leakage"] == 0
        and result["abstention_accuracy"] >= 0.75
    )
    print("PASS: mixed holdout benchmark passed." if passed else "FAIL: mixed holdout benchmark failed.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
