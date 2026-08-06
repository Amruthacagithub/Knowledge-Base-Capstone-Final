"""Evaluate three-way NLI claim verification on frozen evidence pairs."""
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "claim-verification-evaluation-only-32")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import NLI_MODEL
from backend.services.claim_verifier import NLI_LABELS, NLIScorer, verify_claim


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "claim_verification_v1.json"
VERIFICATION_LABELS = ("supported", "conflicting", "insufficient")


def evaluate(
    dataset_path: Path = DATASET_PATH,
    *,
    scorer: NLIScorer | None = None,
) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes.decode("utf-8"))
    confusion = Counter()
    failures = []
    for case in dataset["cases"]:
        result = verify_claim(
            case["claim"],
            [case["evidence"]],
            scorer=scorer,
        )
        expected = case["expected"]
        confusion[(expected, result.label)] += 1
        if result.label != expected:
            failures.append(
                {
                    "id": case["id"],
                    "expected": expected,
                    "predicted": result.label,
                    "confidence": result.confidence,
                    "scores": {
                        label: result.scores[label]
                        for label in NLI_LABELS
                    },
                }
            )
    per_class = {
        label: _class_metrics(confusion, label)
        for label in VERIFICATION_LABELS
    }
    cases = len(dataset["cases"])
    correct = sum(confusion[(label, label)] for label in VERIFICATION_LABELS)
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "model": NLI_MODEL,
        "cases": cases,
        "accuracy": correct / cases,
        "macro_f1": sum(item["f1"] for item in per_class.values()) / len(per_class),
        "per_class": per_class,
        "failures": failures,
    }


def _class_metrics(confusion: Counter, label: str) -> dict[str, float]:
    true_positive = confusion[(label, label)]
    predicted = sum(confusion[(expected, label)] for expected in VERIFICATION_LABELS)
    expected = sum(confusion[(label, actual)] for actual in VERIFICATION_LABELS)
    precision = true_positive / predicted if predicted else 1.0
    recall = true_positive / expected if expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    passed = result["macro_f1"] >= 0.85
    print(
        "PASS: claim verification benchmark passed."
        if passed
        else "FAIL: claim verification benchmark failed."
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())