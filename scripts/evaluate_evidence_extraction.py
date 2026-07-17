"""Evaluate deterministic evidence extraction against the versioned seed set."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.evidence_extractor import extract_chunk_evidence


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "evidence_extraction_v1.json"
CORPUS_DATASET_PATH = ROOT / "evaluation" / "evidence_extraction_corpus_v1.json"
ADVERSARIAL_DATASET_PATH = ROOT / "evaluation" / "evidence_extraction_adversarial_v1.json"
MINIMUM_F1 = {
    "entities": 0.75,
    "relationships": 0.70,
    "claims": 0.75,
}


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    cases = json.loads(dataset_bytes.decode("utf-8"))
    totals = {
        name: {"true_positive": 0, "predicted": 0, "expected": 0}
        for name in MINIMUM_F1
    }
    failures = []

    for case in cases:
        _validate_source_excerpt(case)
        evidence = extract_chunk_evidence(case["id"], case["text"])
        entity_names = {entity.id: entity.canonical_name for entity in evidence.entities}
        predicted = {
            "entities": {
                (entity.entity_type, entity.canonical_name)
                for entity in evidence.entities
            },
            "relationships": {
                (
                    entity_names[relationship.source_entity_id],
                    relationship.relationship_type,
                    entity_names[relationship.target_entity_id],
                )
                for relationship in evidence.relationships
            },
            "claims": {
                (claim.predicate, claim.polarity) for claim in evidence.claims
            },
        }
        expected = {
            name: {tuple(item) for item in case[name]}
            for name in MINIMUM_F1
        }
        for name in MINIMUM_F1:
            totals[name]["true_positive"] += len(predicted[name] & expected[name])
            totals[name]["predicted"] += len(predicted[name])
            totals[name]["expected"] += len(expected[name])
            if predicted[name] != expected[name]:
                failures.append(
                    {
                        "id": case["id"],
                        "category": name,
                        "missing": sorted(expected[name] - predicted[name]),
                        "unexpected": sorted(predicted[name] - expected[name]),
                    }
                )

    metrics = {name: _metrics(values) for name, values in totals.items()}
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(cases),
        "metrics": metrics,
        "failures": failures,
    }


def _metrics(values: dict) -> dict:
    true_positive = values["true_positive"]
    precision = true_positive / values["predicted"] if values["predicted"] else 1.0
    recall = true_positive / values["expected"] if values["expected"] else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, **values}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_PATH,
        help="Dataset path relative to the repository root or absolute path",
    )
    parser.add_argument(
        "--no-threshold",
        action="store_true",
        help="Report metrics without failing declared seed thresholds",
    )
    args = parser.parse_args()
    dataset_path = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    result = evaluate(dataset_path)
    print(json.dumps(result, indent=2))
    if args.no_threshold:
        return 0
    failed_thresholds = [
        name
        for name, minimum in MINIMUM_F1.items()
        if result["metrics"][name]["f1"] < minimum
    ]
    if failed_thresholds:
        print(f"FAIL: thresholds not met for {', '.join(failed_thresholds)}")
        return 1
    print("PASS: all extraction seed thresholds met.")
    return 0


def _validate_source_excerpt(case: dict) -> None:
    source_file = case.get("source_file")
    if not source_file:
        return
    source_path = (ROOT / source_file).resolve()
    source_path.relative_to(ROOT)
    source_text = source_path.read_text(encoding="utf-8")
    if case["text"] not in source_text:
        raise ValueError(
            f"Case {case['id']} text is not an exact excerpt of {source_file}"
        )


if __name__ == "__main__":
    raise SystemExit(main())