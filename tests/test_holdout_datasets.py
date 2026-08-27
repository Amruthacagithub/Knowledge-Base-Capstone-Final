import json
from collections import Counter
from pathlib import Path

from scripts.evaluate_claim_verification import VERIFICATION_LABELS
from scripts.evaluate_holdouts import (
    CLAIM_HOLDOUT,
    EXTRACTION_HOLDOUT,
    PLANNER_HOLDOUT,
    THRESHOLDS,
)


ROOT = Path(__file__).resolve().parents[1]


def test_extraction_holdout_schema_and_sources():
    cases = json.loads(EXTRACTION_HOLDOUT.read_text(encoding="utf-8"))
    assert len(cases) == 24
    assert len({case["id"] for case in cases}) == 24
    for case in cases:
        source_path = (ROOT / case["source_file"]).resolve()
        assert source_path.exists()
        assert case["text"] in source_path.read_text(encoding="utf-8")


def test_claim_holdout_is_balanced():
    dataset = json.loads(CLAIM_HOLDOUT.read_text(encoding="utf-8"))
    cases = dataset["cases"]
    assert len(cases) == 24
    assert Counter(case["expected"] for case in cases) == {
        label: 8 for label in VERIFICATION_LABELS
    }
    assert len({case["id"] for case in cases}) == 24


def test_planner_holdout_distribution():
    dataset = json.loads(PLANNER_HOLDOUT.read_text(encoding="utf-8"))
    cases = dataset["cases"]
    assert len(cases) == 25
    assert Counter(case["route"] for case in cases) == {
        route: 5 for route in dataset["routes"]
    }
    assert len({case["query"] for case in cases}) == 25


def test_holdout_hashes_are_stable():
    for path in (EXTRACTION_HOLDOUT, CLAIM_HOLDOUT, PLANNER_HOLDOUT):
        first = path.read_bytes()
        second = path.read_bytes()
        assert first == second


def test_holdout_threshold_constants():
    assert THRESHOLDS["extraction_entity_f1"] >= 0.8
    assert THRESHOLDS["claim_macro_f1"] >= 0.8
