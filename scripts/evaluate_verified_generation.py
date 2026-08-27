"""Evaluate verified rendering, citation faithfulness, and malformed safety."""
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "verified-generation-evaluation-only-32")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.claim_verifier import CrossEncoderNLIScorer
from backend.services.generator import generate_verified_answer
from scripts.evaluate_claim_verification import DATASET_PATH


ROOT = Path(__file__).resolve().parent.parent
EVALUATION_QUESTION = "Evaluation question"
MALFORMED_CASES = (
    "This is unstructured prose with a false claim [1].",
    "```json\n{\"claims\": []}\n```",
    '{"claims": [], "answer": "Unsupported prose"}',
    '{"claims": [{"text": "False claim", "evidence_markers": [0]}]}',
)


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes.decode("utf-8"))
    scorer = CrossEncoderNLIScorer()
    expected_supported = 0
    emitted = 0
    faithful = 0
    supported_emitted = 0
    failures = []

    for case in dataset["cases"]:
        chunk = _chunk(case["id"], case["evidence"])
        model_output = json.dumps(
            {
                "claims": [
                    {"text": case["claim"], "evidence_markers": [1]}
                ]
            }
        )
        result = generate_verified_answer(
            EVALUATION_QUESTION,
            [chunk],
            text_generator=lambda prompt, output=model_output: output,
            scorer=scorer,
        )
        rendered = case["claim"] in result["answer"]
        cited = [citation["marker"] for citation in result["citations"]] == [1]
        if case["expected"] == "supported":
            expected_supported += 1
        if rendered:
            emitted += 1
            faithful += int(case["expected"] == "supported" and cited)
            supported_emitted += int(case["expected"] == "supported")
        expected_rendered = case["expected"] == "supported"
        if rendered != expected_rendered or (rendered and not cited):
            failures.append(
                {
                    "id": case["id"],
                    "expected": case["expected"],
                    "status": result["claims"][0]["status"],
                    "rendered": rendered,
                    "cited": cited,
                }
            )

    malformed_safe = sum(_malformed_case_is_safe(raw) for raw in MALFORMED_CASES)
    invalid_marker_safe = _invalid_marker_is_safe()
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(dataset["cases"]),
        "citation_faithfulness": faithful / emitted if emitted else 1.0,
        "unsupported_claim_rate": (
            (emitted - supported_emitted) / emitted if emitted else 0.0
        ),
        "supported_answer_completeness": supported_emitted / expected_supported,
        "malformed_output_safe_rate": malformed_safe / len(MALFORMED_CASES),
        "invalid_marker_safe": invalid_marker_safe,
        "failures": failures,
    }


def _chunk(case_id: str, evidence: str) -> dict:
    return {
        "chunk_id": f"{case_id}-chunk",
        "doc_id": f"{case_id}-document",
        "doc_title": "Evaluation Source",
        "department": "Evaluation",
        "text": evidence,
        "file_type": "markdown",
    }


def _malformed_case_is_safe(raw_output: str) -> bool:
    result = generate_verified_answer(
        EVALUATION_QUESTION,
        [_chunk("malformed", "The verified value is 20.")],
        text_generator=lambda prompt: raw_output,
    )
    return (
        result["claims"] == []
        and "false claim" not in result["answer"].casefold()
        and "unsupported prose" not in result["answer"].casefold()
        and [citation["marker"] for citation in result["citations"]] == [1]
    )


def _invalid_marker_is_safe() -> bool:
    result = generate_verified_answer(
        EVALUATION_QUESTION,
        [_chunk("invalid-marker", "The verified value is 20.")],
        text_generator=lambda prompt: (
            '{"claims":[{"text":"The value is 99.",'
            '"evidence_markers":[2]}]}'
        ),
    )
    return (
        result["claims"][0]["status"] == "insufficient"
        and "99" not in result["answer"]
        and result["citations"] == []
    )


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    passed = (
        result["citation_faithfulness"] >= 0.95
        and result["unsupported_claim_rate"] <= 0.05
        and result["supported_answer_completeness"] >= 0.90
        and result["malformed_output_safe_rate"] >= 1.0
        and result["invalid_marker_safe"]
    )
    print(
        "PASS: verified generation benchmark passed."
        if passed
        else "FAIL: verified generation benchmark failed."
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())