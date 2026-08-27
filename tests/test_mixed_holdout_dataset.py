import json
from collections import Counter

from scripts.evaluate_mixed_holdout import DATASET_PATH


def test_mixed_holdout_has_120_unique_cases():
    if not DATASET_PATH.exists():
        from scripts.generate_mixed_holdout import main as generate

        generate()
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases = dataset["cases"]
    assert len(cases) == 120
    assert len({case["id"] for case in cases}) == 120
    assert len({case["query"] for case in cases}) == 120


def test_mixed_holdout_slice_distribution():
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    counts = Counter(case["slice"] for case in dataset["cases"])
    assert counts["local"] == 25
    assert counts["global"] == 15
    assert counts["multi_hop"] == 20
    assert counts["temporal"] == 20
    assert counts["comparison"] == 10
    assert counts["abstain"] == 15
    assert counts["denied_access"] == 15
