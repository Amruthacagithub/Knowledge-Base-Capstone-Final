"""Bounded hybrid retrieval fan-out for deterministic query plans."""
from collections.abc import Callable

from backend.services.auth import UserContext
from backend.services.query_planner import QueryPlan


HybridSearch = Callable[..., tuple[list[dict], str]]
MAX_PLANNED_CANDIDATES = 30


def retrieve_for_plan(
    query: str,
    user_ctx: UserContext,
    department_filter: str | None,
    plan: QueryPlan,
    *,
    search_fn: HybridSearch,
) -> tuple[list[dict], str]:
    """Run bounded subqueries and merge only permission-filtered search outputs."""
    queries = (query, *plan.subqueries)
    primary_results, query_type = search_fn(
        query=query,
        user_ctx=user_ctx,
        department_filter=department_filter,
    )
    if len(queries) == 1:
        return primary_results, query_type

    result_sets = [primary_results]
    for subquery in queries[1:]:
        results, _ = search_fn(
            query=subquery,
            user_ctx=user_ctx,
            department_filter=department_filter,
        )
        result_sets.append(results)
    return _merge_result_sets(result_sets), query_type


def _merge_result_sets(result_sets: list[list[dict]]) -> list[dict]:
    merged = {}
    for results in result_sets:
        for rank, result in enumerate(results):
            key = _candidate_key(result)
            if key not in merged:
                merged[key] = {**result, "planner_rrf": 0.0}
            merged[key]["planner_rrf"] += 1.0 / (60 + rank)
    ordered = sorted(
        merged.values(),
        key=lambda result: (-result["planner_rrf"], _candidate_key(result)),
    )
    return ordered[:MAX_PLANNED_CANDIDATES]


def merge_authorized_candidates(
    primary: list[dict],
    supplemental: list[dict],
) -> list[dict]:
    """Merge two independently authorized candidate sets by canonical identity."""
    merged = {_candidate_key(candidate): dict(candidate) for candidate in primary}
    for candidate in supplemental:
        key = _candidate_key(candidate)
        if key not in merged:
            merged[key] = dict(candidate)
            continue
        existing = merged[key]
        existing["score"] = max(
            float(existing.get("score", 0.0)),
            float(candidate.get("score", 0.0)),
        )
        for field in ("graph_relationship_ids", "graph_entity_ids"):
            if candidate.get(field):
                existing[field] = list(candidate[field])
    return sorted(
        merged.values(),
        key=lambda candidate: (
            -float(candidate.get("score", 0.0)),
            _candidate_key(candidate),
        ),
    )[:MAX_PLANNED_CANDIDATES]


def _candidate_key(result: dict) -> tuple[str, str, str]:
    if result.get("chunk_id"):
        return ("chunk", str(result["chunk_id"]), "")
    return (
        "legacy",
        str(result.get("doc_id", "")),
        str(result.get("chunk_index", result.get("text", ""))),
    )