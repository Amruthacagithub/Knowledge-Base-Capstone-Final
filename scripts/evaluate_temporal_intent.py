"""Evaluate deterministic temporal query intent classification."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.query_router import classify_temporal_intent


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "temporal_intent_v1.json"
INTENTS = ("none", "current", "historical", "change")


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    cases = json.loads(dataset_bytes.decode("utf-8"))
    confusion = Counter()
    failures = []
    for index, case in enumerate(cases):
        predicted = classify_temporal_intent(case["query"])
        expected = case["intent"]
        confusion[(expected, predicted)] += 1
        if predicted != expected:
            failures.append(
                {
                    "index": index,
                    "query": case["query"],
                    "expected": expected,
                    "predicted": predicted,
                }
            )
    per_class = {
        intent: _class_metrics(confusion, intent)
        for intent in INTENTS
    }
    accuracy = (len(cases) - len(failures)) / len(cases)
    macro_f1 = sum(metrics["f1"] for metrics in per_class.values()) / len(INTENTS)
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(cases),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "failures": failures,
    }


def _class_metrics(confusion: Counter, intent: str) -> dict:
    true_positive = confusion[(intent, intent)]
    predicted = sum(confusion[(expected, intent)] for expected in INTENTS)
    expected = sum(confusion[(intent, actual)] for actual in INTENTS)
    precision = true_positive / predicted if predicted else 1.0
    recall = true_positive / expected if expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    passed = result["accuracy"] >= 0.90 and result["macro_f1"] >= 0.90
    print("PASS: temporal intent benchmark passed." if passed else "FAIL: temporal intent benchmark failed.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())