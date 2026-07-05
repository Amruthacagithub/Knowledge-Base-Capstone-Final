from backend.services.auth import UserContext
from backend.services.planned_retrieval import retrieve_for_plan
from backend.services.query_planner import QueryPlan


USER = UserContext(
    user_id="planner-user",
    email="planner@example.com",
    department="Engineering",
    roles=["Employee", "Engineer"],
)


def _candidate(chunk_id, score=1.0):
    return {
        "chunk_id": chunk_id,
        "doc_id": f"doc-{chunk_id}",
        "text": chunk_id,
        "score": score,
    }


def test_local_plan_preserves_single_search_results():
    expected = [_candidate("one"), _candidate("two")]
    calls = []

    def search_fn(**kwargs):
        calls.append(kwargs)
        return expected, "conceptual"

    results, query_type = retrieve_for_plan(
        "PTO policy",
        USER,
        None,
        QueryPlan(route="local", subqueries=()),
        search_fn=search_fn,
    )

    assert results is expected
    assert query_type == "conceptual"
    assert len(calls) == 1


def test_fanout_reuses_authorization_and_deduplicates_chunks():
    calls = []
    result_sets = {
        "Compare A and B": [_candidate("shared"), _candidate("primary")],
        "A": [_candidate("a"), _candidate("shared")],
        "B": [_candidate("b"), _candidate("shared")],
    }

    def search_fn(**kwargs):
        calls.append(kwargs)
        return result_sets[kwargs["query"]], "conceptual"

    results, _ = retrieve_for_plan(
        "Compare A and B",
        USER,
        "Engineering",
        QueryPlan(route="comparison", subqueries=("A", "B")),
        search_fn=search_fn,
    )

    assert [result["chunk_id"] for result in results][0] == "shared"
    assert {result["chunk_id"] for result in results} == {
        "shared",
        "primary",
        "a",
        "b",
    }
    assert len(calls) == 3
    assert all(call["user_ctx"] is USER for call in calls)
    assert all(call["department_filter"] == "Engineering" for call in calls)