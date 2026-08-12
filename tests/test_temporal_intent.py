from scripts.evaluate_temporal_intent import DATASET_PATH, evaluate


def test_temporal_intent_benchmark_meets_accuracy_gate():
    result = evaluate(DATASET_PATH)

    assert result["cases"] == 24
    assert result["accuracy"] >= 0.90
    assert result["macro_f1"] >= 0.90