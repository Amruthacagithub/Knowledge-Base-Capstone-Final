from backend.models import QueryExecutionTrace
from backend.services.auth import UserContext
from backend.services.query_planner import QueryPlan
from backend.services.query_trace import stage_query_trace


def test_query_trace_contains_ids_and_outcomes_but_no_query_or_claim_text(db_session):
    user = UserContext(
        user_id="trace-user",
        email="trace@example.com",
        department="Engineering",
        roles=["Employee", "Engineer"],
    )
    query = "restricted payroll question"
    claim_text = "A sensitive generated claim."

    trace_id = stage_query_trace(
        db_session,
        user,
        query,
        QueryPlan(route="multi_hop", subqueries=("payroll",)),
        candidate_ids=["chunk-1", "chunk-1", "chunk-2"],
        graph_trace_ids=["graph-trace-1"],
        timings={"retrieval_ms": 10, "rerank_ms": 5, "total_ms": 20},
        claims=[
            {
                "id": "claim-1",
                "text": claim_text,
                "status": "supported",
                "confidence": 0.9,
                "evidence_ids": ["chunk-1"],
            }
        ],
        corrective_retrieval_used=True,
    )

    trace = db_session.get(QueryExecutionTrace, trace_id)
    serialized = str(trace.__dict__)
    assert trace.query_hash and len(trace.query_hash) == 64
    assert trace.candidate_ids_json == ["chunk-1", "chunk-2"]
    assert trace.verification_json == [
        {
            "claim_id": "claim-1",
            "status": "supported",
            "confidence": 0.9,
            "evidence_ids": ["chunk-1"],
        }
    ]
    assert query not in serialized
    assert claim_text not in serialized