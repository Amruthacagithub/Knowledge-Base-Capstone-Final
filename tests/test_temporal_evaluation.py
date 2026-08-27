from scripts.evaluate_temporal_conflicts import DATASET_PATH, evaluate


def test_temporal_benchmark_meets_selection_conflict_and_visibility_gates():
    result = evaluate(DATASET_PATH)

    assert result["cases"] == 12
    assert result["exact_case_accuracy"] >= 0.90
    assert result["conflict_precision"] >= 0.90
    assert result["conflict_recall"] >= 0.90
    assert result["conflict_f1"] >= 0.90