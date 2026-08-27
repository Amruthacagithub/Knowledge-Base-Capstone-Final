from scripts.evaluate_ablations import (
    _all_local_baseline,
    _current_only_temporal_baseline,
    _no_graph_baseline,
    _no_quarantine_baseline,
    _unverified_baseline,
)


def test_all_local_planner_baseline_penalizes_non_local_routes():
    dataset = {
        "routes": ["local", "global", "multi_hop", "temporal", "comparison"],
        "cases": [{"route": route} for route in (
            "local",
            "global",
            "multi_hop",
            "temporal",
            "comparison",
        )],
    }

    result = _all_local_baseline(dataset)

    assert result["accuracy"] == 0.2
    assert result["macro_f1"] < 0.1


def test_unverified_baseline_counts_non_supported_claims_as_unsupported():
    dataset = {
        "cases": [
            {"expected": "supported"},
            {"expected": "conflicting"},
            {"expected": "insufficient"},
        ]
    }

    result = _unverified_baseline(dataset)

    assert result["citation_faithfulness"] == 1 / 3
    assert result["unsupported_claim_rate"] == 2 / 3


def test_structural_baselines_report_missing_capabilities():
    temporal = _current_only_temporal_baseline(
        [{"intent": "historical"}, {"intent": "change"}, {"intent": "current"}]
    )
    graph = _no_graph_baseline(
        {"cases": [{"expected_paths": [["a", "b"]]}, {"expected_paths": []}]}
    )
    safety = _no_quarantine_baseline(
        {"cases": [{"unsafe": True}, {"unsafe": False}]}
    )

    assert temporal == {"historical_or_change_coverage": 0.0, "cases": 2}
    assert graph["path_recall"] == 0.0
    assert graph["exact_case_accuracy"] == 0.5
    assert safety == {"unsafe_recall": 0.0, "unsafe_cases": 1}