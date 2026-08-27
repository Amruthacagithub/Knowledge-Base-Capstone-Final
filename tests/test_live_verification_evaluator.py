import json

from scripts.evaluate_live_verified_generation import DATASET_PATH, evaluate


def test_live_verification_dataset_schema():
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    assert len(dataset["cases"]) == 20
    assert len({case["id"] for case in dataset["cases"]}) == 20


def test_live_verification_benchmark_runs():
    result = evaluate()
    assert result["cases"] == 20
    assert result["abstention_accuracy"] >= 0.80
