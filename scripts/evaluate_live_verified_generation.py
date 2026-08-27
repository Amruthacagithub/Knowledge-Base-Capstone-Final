"""Evaluate live/offline verified generation on frozen local cases."""
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "live-verification-eval-only-32-chars")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.claim_verifier import CrossEncoderNLIScorer
from backend.services.generator import generate_verified_answer


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "live_verification_v1.json"


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes.decode("utf-8"))
    scorer = CrossEncoderNLIScorer()
    faithful = 0
    emitted = 0
    abstain_expected = 0
    abstain_correct = 0
    failures = []

    supported_emitted = 0
    unsupported_emitted = 0
    for case in dataset["cases"]:
        chunk = {
            "chunk_id": case["id"],
            "doc_id": f"doc-{case['id']}",
            "doc_title": "Evaluation",
            "department": "Engineering",
            "text": case["evidence"],
            "file_type": "markdown",
            "score": 1.0,
        }
        model_output = json.dumps(
            {"claims": [{"text": case["claim"], "evidence_markers": [1]}]}
        )
        result = generate_verified_answer(
            "Local verification evaluation question",
            [chunk],
            text_generator=lambda prompt, output=model_output: output,
            scorer=scorer,
        )
        rendered = case["claim"] in result["answer"]
        status = result["claims"][0]["status"] if result["claims"] else "insufficient"
        if rendered:
            emitted += 1
            if case["must_render"] and status == "supported":
                faithful += 1
                supported_emitted += 1
            elif case["must_render"] and status != "supported":
                unsupported_emitted += 1
        if not case["must_render"]:
            abstain_expected += 1
            abstain_correct += int(not rendered)
        if rendered != case["must_render"] or status != case["expected_status"]:
            failures.append(
                {
                    "id": case["id"],
                    "expected_status": case["expected_status"],
                    "status": status,
                    "must_render": case["must_render"],
                    "rendered": rendered,
                }
            )

    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(dataset["cases"]),
        "citation_faithfulness": faithful / emitted if emitted else 1.0,
        "unsupported_claim_rate": unsupported_emitted / emitted if emitted else 0.0,
        "abstention_accuracy": (
            abstain_correct / abstain_expected if abstain_expected else 1.0
        ),
        "failures": failures,
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    passed = (
        result["citation_faithfulness"] >= 0.85
        and result["abstention_accuracy"] >= 0.80
        and result["unsupported_claim_rate"] <= 0.05
        and len(result["failures"]) <= 6
    )
    print("PASS: live verification benchmark passed." if passed else "FAIL: live verification benchmark failed.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
