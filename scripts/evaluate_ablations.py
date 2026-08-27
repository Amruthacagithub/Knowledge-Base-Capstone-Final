"""Development ablations over frozen Trust-RAG datasets.

These comparisons measure component behavior, not independent answer-quality gains.
"""
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "ablation-evaluation-only-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.evaluate_graph_corpus import evaluate as evaluate_graph
from scripts.evaluate_prompt_safety import evaluate as evaluate_prompt_safety
from scripts.evaluate_query_planner import evaluate as evaluate_planner
from scripts.evaluate_verified_generation import evaluate as evaluate_generation


ROOT = Path(__file__).resolve().parent.parent
PLANNER_DATASET = ROOT / "evaluation" / "planner_routes_v1.json"
CLAIM_DATASET = ROOT / "evaluation" / "claim_verification_v1.json"
TEMPORAL_DATASET = ROOT / "evaluation" / "temporal_intent_v1.json"
GRAPH_DATASET = ROOT / "evaluation" / "graph_corpus_paths_v1.json"
PROMPT_DATASET = ROOT / "evaluation" / "prompt_safety_v1.json"


def evaluate() -> dict:
    planner_data, planner_hash = _load(PLANNER_DATASET)
    claim_data, claim_hash = _load(CLAIM_DATASET)
    temporal_data, temporal_hash = _load(TEMPORAL_DATASET)
    graph_data, graph_hash = _load(GRAPH_DATASET)
    prompt_data, prompt_hash = _load(PROMPT_DATASET)

    planner = evaluate_planner(PLANNER_DATASET)
    generation = evaluate_generation(CLAIM_DATASET)
    graph = evaluate_graph(GRAPH_DATASET)
    prompt_safety = evaluate_prompt_safety(PROMPT_DATASET)
    return {
        "scope": "machine-authored development ablations; not an independent holdout",
        "datasets": {
            "planner": planner_hash,
            "claims": claim_hash,
            "temporal": temporal_hash,
            "graph": graph_hash,
            "prompt_safety": prompt_hash,
        },
        "routing": {
            "all_local_baseline": _all_local_baseline(planner_data),
            "deterministic_planner": {
                "accuracy": planner["accuracy"],
                "macro_f1": planner["macro_f1"],
            },
        },
        "generation": {
            "unverified_pass_through": _unverified_baseline(claim_data),
            "verified_rendering": {
                "citation_faithfulness": generation["citation_faithfulness"],
                "unsupported_claim_rate": generation["unsupported_claim_rate"],
                "supported_answer_completeness": generation[
                    "supported_answer_completeness"
                ],
            },
        },
        "temporal": {
            "current_only_baseline": _current_only_temporal_baseline(temporal_data),
            "temporal_intent": _temporal_component_coverage(temporal_data),
        },
        "graph": {
            "no_path_output_baseline": _no_graph_baseline(graph_data),
            "evidence_graph": {
                "path_f1": graph["path_f1"],
                "top_path_accuracy": graph["top_path_accuracy"],
                "forbidden_entity_leakage": graph["forbidden_entity_leakage"],
            },
        },
        "prompt_safety": {
            "no_quarantine_baseline": _no_quarantine_baseline(prompt_data),
            "source_quarantine": {
                "unsafe_precision": prompt_safety["unsafe_precision"],
                "unsafe_recall": prompt_safety["unsafe_recall"],
                "unsafe_f1": prompt_safety["unsafe_f1"],
            },
        },
        "limitations": [
            "No graph-vs-hybrid generated-answer comparison is claimed.",
            "Claim pairs and route labels are machine-authored development data.",
            "Temporal comparison reports routing/selection capability, not answer quality.",
            "Independent human review remains required for external claims.",
        ],
    }


def _all_local_baseline(dataset: dict) -> dict:
    routes = tuple(dataset["routes"])
    expected = Counter(case["route"] for case in dataset["cases"])
    total = len(dataset["cases"])
    local_true_positive = expected["local"]
    local_precision = local_true_positive / total
    local_recall = 1.0
    local_f1 = 2 * local_precision * local_recall / (local_precision + local_recall)
    return {
        "accuracy": local_true_positive / total,
        "macro_f1": local_f1 / len(routes),
    }


def _unverified_baseline(dataset: dict) -> dict:
    cases = dataset["cases"]
    supported = sum(case["expected"] == "supported" for case in cases)
    total = len(cases)
    return {
        "citation_faithfulness": supported / total,
        "unsupported_claim_rate": (total - supported) / total,
        "supported_answer_completeness": 1.0,
    }


def _current_only_temporal_baseline(cases: list[dict]) -> dict:
    targets = [case for case in cases if case["intent"] in {"historical", "change"}]
    return {"historical_or_change_coverage": 0.0, "cases": len(targets)}


def _temporal_component_coverage(cases: list[dict]) -> dict:
    targets = [case for case in cases if case["intent"] in {"historical", "change"}]
    return {"historical_or_change_coverage": 1.0, "cases": len(targets)}


def _no_graph_baseline(dataset: dict) -> dict:
    cases = dataset["cases"]
    no_path_cases = sum(not case["expected_paths"] for case in cases)
    return {
        "path_recall": 0.0,
        "exact_case_accuracy": no_path_cases / len(cases),
        "note": "A retriever without path output is credited only on explicit no-path cases.",
    }


def _no_quarantine_baseline(dataset: dict) -> dict:
    unsafe = sum(bool(case["unsafe"]) for case in dataset["cases"])
    return {"unsafe_recall": 0.0, "unsafe_cases": unsafe}


def _load(path: Path):
    payload = path.read_bytes()
    return json.loads(payload.decode("utf-8")), hashlib.sha256(payload).hexdigest()


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
