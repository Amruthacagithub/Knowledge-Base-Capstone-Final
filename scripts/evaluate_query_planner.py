"""Evaluate deterministic five-route query planning."""
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "query-planner-evaluation-only-32-chars")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.query_planner import classify_planner_route


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "planner_routes_v1.json"


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes.decode("utf-8"))
    routes = tuple(dataset["routes"])
    confusion = Counter()
    failures = []
    for case in dataset["cases"]:
        predicted = classify_planner_route(case["query"])
        expected = case["route"]
        confusion[(expected, predicted)] += 1
        if predicted != expected:
            failures.append(
                {
                    "query": case["query"],
                    "expected": expected,
                    "predicted": predicted,
                }
            )
    per_route = {
        route: _class_metrics(confusion, route, routes)
        for route in routes
    }
    case_count = len(dataset["cases"])
    correct = sum(confusion[(route, route)] for route in routes)
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": case_count,
        "accuracy": correct / case_count,
        "macro_f1": sum(item["f1"] for item in per_route.values()) / len(routes),
        "per_route": per_route,
        "failures": failures,
    }


def _class_metrics(confusion: Counter, route: str, routes: tuple[str, ...]) -> dict:
    true_positive = confusion[(route, route)]
    predicted = sum(confusion[(expected, route)] for expected in routes)
    expected = sum(confusion[(route, actual)] for actual in routes)
    precision = true_positive / predicted if predicted else 1.0
    recall = true_positive / expected if expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    passed = result["macro_f1"] >= 0.90
    print(
        "PASS: query planner benchmark passed."
        if passed
        else "FAIL: query planner benchmark failed."
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())