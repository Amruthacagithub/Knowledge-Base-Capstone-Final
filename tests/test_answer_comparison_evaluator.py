import json

from scripts.evaluate_answer_comparison import DATASET_PATH, evaluate


def test_answer_comparison_dataset_schema():
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    assert len(dataset["cases"]) >= 10
    assert len({case["id"] for case in dataset["cases"]}) == len(dataset["cases"])


def test_answer_comparison_evaluator_runs():
    result = evaluate()
    assert result["cases"] == len(json.loads(DATASET_PATH.read_text())["cases"])
    assert result["forbidden_leakage"] == 0
    assert result["doc_recall"] >= 0.70
