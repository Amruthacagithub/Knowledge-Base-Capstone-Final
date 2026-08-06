"""Evaluate prompt-injection source quarantine rules."""
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "prompt-safety-evaluation-only-32-chars")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.prompt_safety import assess_source_text


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "prompt_safety_v1.json"


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes.decode("utf-8"))
    true_positive = false_positive = false_negative = correct = 0
    failures = []
    for case in dataset["cases"]:
        predicted = assess_source_text(case["text"]).unsafe
        expected = bool(case["unsafe"])
        correct += int(predicted == expected)
        true_positive += int(predicted and expected)
        false_positive += int(predicted and not expected)
        false_negative += int(not predicted and expected)
        if predicted != expected:
            failures.append(
                {"id": case["id"], "expected": expected, "predicted": predicted}
            )
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(dataset["cases"]),
        "accuracy": correct / len(dataset["cases"]),
        "unsafe_precision": precision,
        "unsafe_recall": recall,
        "unsafe_f1": f1,
        "failures": failures,
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    passed = (
        result["accuracy"] >= 0.95
        and result["unsafe_precision"] >= 0.95
        and result["unsafe_recall"] >= 0.95
    )
    print(
        "PASS: prompt safety benchmark passed."
        if passed
        else "FAIL: prompt safety benchmark failed."
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())