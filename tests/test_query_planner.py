from backend.services.query_planner import (
    classify_planner_route,
    plan_query,
    validate_subqueries,
)
from scripts.evaluate_query_planner import DATASET_PATH, evaluate


def test_temporal_precedes_comparison():
    assert (
        classify_planner_route("Compare the previous and current policies")
        == "temporal"
    )


def test_explicit_subject_comparison_route():
    assert classify_planner_route("Compare PTO and parental leave") == "comparison"


def test_dependency_chain_route():
    assert classify_planner_route("Trace the dependency chain to Stripe") == "multi_hop"


def test_corpus_summary_route():
    assert classify_planner_route("Summarize themes across all policies") == "global"


def test_unmarked_question_defaults_local():
    assert classify_planner_route("Who owns Billing Service?") == "local"


def test_subqueries_are_bounded_normalized_and_deduplicated():
    subqueries = validate_subqueries(
        ["  First   query ", "first query", "", "Second", "Third", "Fourth", "Fifth"]
    )

    assert subqueries == ("First query", "Second", "Third", "Fourth")


def test_plan_carries_validated_subqueries():
    plan = plan_query("Compare A and B", proposed_subqueries=["A", "B"])

    assert plan.route == "comparison"
    assert plan.subqueries == ("A", "B")


def test_comparison_plan_derives_subject_subqueries():
    plan = plan_query("Compare PTO and parental leave")

    assert plan.subqueries == ("PTO", "parental leave")


def test_global_plan_uses_bounded_department_coverage():
    plan = plan_query("Summarize themes across all policies")

    assert plan.route == "global"
    assert plan.subqueries == (
        "HR policies",
        "Engineering systems",
        "Sales operations",
    )


def test_planner_benchmark_meets_macro_f1_gate():
    result = evaluate(DATASET_PATH)

    assert result["cases"] == 50
    assert result["macro_f1"] >= 0.90