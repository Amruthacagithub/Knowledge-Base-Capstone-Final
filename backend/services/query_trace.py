"""Privacy-preserving route-general query execution traces."""
import uuid

from backend.models import QueryExecutionTrace
from backend.services.audit import query_fingerprint
from backend.services.auth import UserContext
from backend.services.query_planner import QueryPlan


_TIMING_KEYS = ("retrieval_ms", "rerank_ms", "generation_ms", "total_ms")
_VERIFICATION_STATUSES = {"supported", "conflicting", "insufficient"}


def stage_query_trace(
    db,
    user_ctx: UserContext,
    query: str,
    plan: QueryPlan,
    *,
    candidate_ids: list[str],
    graph_trace_ids: list[str],
    timings: dict[str, int],
    claims: list[dict],
    corrective_retrieval_used: bool,
) -> str:
    """Stage one ID-only trace in the caller's transaction."""
    trace_id = str(uuid.uuid4())
    db.add(
        QueryExecutionTrace(
            id=trace_id,
            user_id=user_ctx.user_id,
            query_hash=query_fingerprint(query),
            query_length=len(query),
            route=plan.route,
            subquery_count=len(plan.subqueries),
            candidate_ids_json=_bounded_unique(candidate_ids, 100),
            graph_trace_ids_json=_bounded_unique(graph_trace_ids, 20),
            timings_json={
                key: max(0, int(timings.get(key, 0)))
                for key in _TIMING_KEYS
            },
            verification_json=_verification_outcomes(claims),
            corrective_retrieval_used=bool(corrective_retrieval_used),
            authorization_applied=True,
        )
    )
    db.flush()
    return trace_id


def _bounded_unique(values: list[str], limit: int) -> list[str]:
    unique = []
    seen = set()
    for value in values:
        normalized = str(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
        if len(unique) >= limit:
            break
    return unique


def _verification_outcomes(claims: list[dict]) -> list[dict]:
    outcomes = []
    for claim in claims[:20]:
        status = str(claim.get("status", ""))
        if status not in _VERIFICATION_STATUSES:
            continue
        outcomes.append(
            {
                "claim_id": str(claim.get("id", "")),
                "status": status,
                "confidence": min(max(float(claim.get("confidence", 0.0)), 0.0), 1.0),
                "evidence_ids": _bounded_unique(claim.get("evidence_ids", []), 10),
            }
        )
    return outcomes