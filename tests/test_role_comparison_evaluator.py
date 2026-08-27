from scripts.evaluate_role_comparison import evaluate


def test_role_comparison_has_zero_leakage():
    result = evaluate()
    assert result["leakage_count"] == 0
    assert result["checks"] >= 4
