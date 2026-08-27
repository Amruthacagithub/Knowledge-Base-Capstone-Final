from scripts.evaluate_evidence_extraction import (
    ADVERSARIAL_DATASET_PATH,
    CORPUS_DATASET_PATH,
    DATASET_PATH,
    MINIMUM_F1,
    evaluate,
)


def test_evidence_seed_benchmark_meets_declared_thresholds():
    result = evaluate(DATASET_PATH)

    assert result["cases"] == 12
    for category, minimum in MINIMUM_F1.items():
        assert result["metrics"][category]["f1"] >= minimum


def test_corpus_benchmark_is_source_verifiable_and_frozen():
    result = evaluate(CORPUS_DATASET_PATH)

    assert result["cases"] == 24
    assert len(result["sha256"]) == 64


def test_adversarial_benchmark_is_frozen_before_next_extractor_changes():
    result = evaluate(ADVERSARIAL_DATASET_PATH)

    assert result["cases"] == 24
    assert len(result["sha256"]) == 64