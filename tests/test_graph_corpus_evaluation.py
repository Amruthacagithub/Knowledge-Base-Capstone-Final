from pathlib import Path

from scripts.evaluate_graph_corpus import DATASET_PATH, ROOT, evaluate


def test_corpus_graph_pipeline_meets_path_and_ranking_gates():
    result = evaluate(DATASET_PATH)

    assert result["cases"] == 10
    assert result["source_errors"] == []
    assert result["exact_case_accuracy"] >= 0.90
    assert result["path_f1"] >= 0.90
    assert result["top_path_accuracy"] >= 0.80
    assert result["forbidden_entity_leakage"] == 0


def test_expanded_corpus_graph_v2_meets_path_gates():
    result = evaluate(ROOT / "evaluation" / "graph_corpus_paths_v2.json")

    assert result["cases"] == 15
    assert result["source_errors"] == []
    assert result["path_f1"] >= 0.90
    assert result["forbidden_entity_leakage"] == 0