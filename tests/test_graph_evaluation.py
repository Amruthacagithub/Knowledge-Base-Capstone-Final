from scripts.evaluate_graph_traversal import DATASET_PATH, evaluate


def test_graph_traversal_matrix_meets_accuracy_and_leakage_gates():
    result = evaluate(DATASET_PATH)

    assert result["cases"] == 12
    assert result["exact_case_accuracy"] >= 0.95
    assert result["path_f1"] >= 0.95
    assert result["forbidden_entity_leakage"] == 0