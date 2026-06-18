"""
Search router — main search/ask endpoint.
"""
import time
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from backend.services.auth import authenticate
from backend.services.retriever import hybrid_search
from backend.services.reranker import rerank
from backend.services.generator import generate_answer
from backend.services.query_planner import plan_query
from backend.services.planned_retrieval import (
    merge_authorized_candidates,
    retrieve_for_plan,
)
from backend.services.graph_retrieval import retrieve_graph_candidates
from backend.config import (
    EVIDENCE_GRAPH_ENABLED,
    SEARCH_RATE_LIMIT_PER_MINUTE,
    TEMPORAL_API_ENABLED,
)
from backend.database import SessionLocal
from backend.services.temporal_search import retrieve_temporal_candidates
from backend.services.audit import log_search
from backend.services.query_trace import stage_query_trace
from backend.services.rate_limit import rate_limiter

router = APIRouter(prefix="/api", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    department_filter: Literal["HR", "Engineering", "Sales"] | None = None


class CitationItem(BaseModel):
    marker: int
    chunk_id: str = ""
    doc_title: str
    doc_id: str
    department: str
    chunk_text: str
    page_start: int | None = None
    page_end: int | None = None
    file_type: str = "markdown"


class VerifiedClaimItem(BaseModel):
    id: str
    text: str
    status: str
    confidence: float
    evidence_ids: list[str]


class QueryPlanItem(BaseModel):
    route: str
    subqueries: list[str]
    corrective_retrieval_used: bool
    trace_ids: list[str] = Field(default_factory=list)
    execution_trace_id: str | None = None


class EvidenceGraphEntityItem(BaseModel):
    id: str
    name: str


class EvidenceGraphRelationshipItem(BaseModel):
    id: str
    source_entity_id: str
    target_entity_id: str
    type: str


class EvidenceGraphPathItem(BaseModel):
    entity_ids: list[str]
    relationship_ids: list[str]
    entities: list[EvidenceGraphEntityItem]
    relationships: list[EvidenceGraphRelationshipItem]
    score: float


class EvidenceGraphItem(BaseModel):
    paths: list[EvidenceGraphPathItem] = Field(default_factory=list)


class SearchResponse(BaseModel):
    answer: str
    citations: list[CitationItem]
    latency_ms: int
    chunks_found: int
    query_type: str
    departments_hit: list[str] = Field(default_factory=list)
    claims: list[VerifiedClaimItem] = Field(default_factory=list)
    query_plan: QueryPlanItem | None = None
    evidence_graph: EvidenceGraphItem = Field(default_factory=EvidenceGraphItem)


@router.post(
    "/search",
    response_model=SearchResponse,
    responses={
        401: {"description": "Invalid or expired token"},
        429: {"description": "Search rate limit exceeded"},
    },
)
def search(req: SearchRequest, authorization: Annotated[str, Header()]):
    """
    Search the knowledge base and get an AI-generated answer.

    Requires a Bearer token from the login endpoint.
    """
    start = time.perf_counter()

    # Authenticate
    token = authorization.replace("Bearer ", "")
    user_ctx = authenticate(token)
    if not user_ctx:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    decision = rate_limiter.check(
        f"search:{user_ctx.user_id}",
        SEARCH_RATE_LIMIT_PER_MINUTE,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail="Search rate limit exceeded",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
    query_plan = plan_query(req.query)

    # Search
    candidates, query_type = retrieve_for_plan(
        req.query,
        user_ctx,
        req.department_filter,
        query_plan,
        search_fn=hybrid_search,
    )
    trace_ids = []
    if EVIDENCE_GRAPH_ENABLED and query_plan.route == "multi_hop":
        db = SessionLocal()
        try:
            graph_result = retrieve_graph_candidates(db, user_ctx, req.query)
            db.commit()
        finally:
            db.close()
        candidates = merge_authorized_candidates(
            candidates,
            list(graph_result.candidates),
        )
        trace_ids = list(graph_result.trace_ids)
    if TEMPORAL_API_ENABLED and query_plan.route == "temporal":
        db = SessionLocal()
        try:
            temporal_candidates = retrieve_temporal_candidates(db, user_ctx, req.query)
        finally:
            db.close()
        candidates = merge_authorized_candidates(candidates, temporal_candidates)
    retrieval_ms = _elapsed_ms(start)

    if not candidates:
        elapsed_ms = _elapsed_ms(start)
        execution_trace_id = _persist_query_trace(
            user_ctx,
            req.query,
            query_plan,
            [],
            trace_ids,
            {
                "retrieval_ms": retrieval_ms,
                "rerank_ms": 0,
                "generation_ms": 0,
                "total_ms": elapsed_ms,
            },
            [],
            False,
        )
        return SearchResponse(
            answer=(
                "I couldn't find any relevant documents matching your question. "
                "Try different keywords, remove the department filter, or check that "
                "you have access to the content you're looking for."
            ),
            citations=[],
            latency_ms=elapsed_ms,
            chunks_found=0,
            query_type=query_type,
            departments_hit=[],
            claims=[],
            evidence_graph=EvidenceGraphItem(),
            query_plan=QueryPlanItem(
                route=query_plan.route,
                subqueries=list(query_plan.subqueries),
                corrective_retrieval_used=False,
                trace_ids=trace_ids,
                execution_trace_id=execution_trace_id,
            ),
        )

    # Rerank
    rerank_start = time.perf_counter()
    ranked = rerank(query=req.query, candidates=candidates, top_n=8)
    rerank_ms = _elapsed_ms(rerank_start)

    # Generate answer
    def corrective_retriever(claim_query: str) -> list[dict]:
        corrective_candidates, _ = hybrid_search(
            query=claim_query,
            user_ctx=user_ctx,
            department_filter=req.department_filter,
        )
        return rerank(
            query=claim_query,
            candidates=corrective_candidates,
            top_n=4,
        )

    generation_start = time.perf_counter()
    result = generate_answer(
        question=req.query,
        ranked_chunks=ranked,
        corrective_retriever=corrective_retriever,
        query_plan=query_plan,
    )
    generation_ms = _elapsed_ms(generation_start)
    plan_payload = result.setdefault(
        "query_plan",
        {
            "route": query_plan.route,
            "subqueries": list(query_plan.subqueries),
            "corrective_retrieval_used": False,
        },
    )
    plan_payload["trace_ids"] = trace_ids

    departments_hit = sorted(
        {result.get("department", "") for result in ranked if result.get("department")}
    )

    # Audit log
    doc_ids = list({result.get("doc_id", "") for result in ranked})
    log_search(
        user_id=user_ctx.user_id,
        query_text=req.query,
        doc_ids=doc_ids,
        allowed=True,
    )

    elapsed_ms = _elapsed_ms(start)
    execution_trace_id = _persist_query_trace(
        user_ctx,
        req.query,
        query_plan,
        [_candidate_id(candidate) for candidate in ranked],
        trace_ids,
        {
            "retrieval_ms": retrieval_ms,
            "rerank_ms": rerank_ms,
            "generation_ms": generation_ms,
            "total_ms": elapsed_ms,
        },
        result.get("claims", []),
        bool(plan_payload.get("corrective_retrieval_used")),
    )
    plan_payload["execution_trace_id"] = execution_trace_id

    return SearchResponse(
        answer=result["answer"],
        citations=[CitationItem(**c) for c in result["citations"]],
        latency_ms=elapsed_ms,
        chunks_found=len(candidates),
        query_type=query_type,
        departments_hit=departments_hit,
        claims=[VerifiedClaimItem(**claim) for claim in result.get("claims", [])],
        evidence_graph=_evidence_graph(ranked),
        query_plan=(
            QueryPlanItem(**result["query_plan"])
            if result.get("query_plan")
            else None
        ),
    )


def _persist_query_trace(
    user_ctx,
    query,
    query_plan,
    candidate_ids,
    trace_ids,
    timings,
    claims,
    corrective_retrieval_used,
) -> str:
    db = SessionLocal()
    try:
        trace_id = stage_query_trace(
            db,
            user_ctx,
            query,
            query_plan,
            candidate_ids=candidate_ids,
            graph_trace_ids=trace_ids,
            timings=timings,
            claims=claims,
            corrective_retrieval_used=corrective_retrieval_used,
        )
        db.commit()
        return trace_id
    finally:
        db.close()


def _candidate_id(candidate: dict) -> str:
    if candidate.get("chunk_id"):
        return str(candidate["chunk_id"])
    return f"{candidate.get('doc_id', '')}:{candidate.get('chunk_index', '')}"


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _evidence_graph(ranked: list[dict]) -> EvidenceGraphItem:
    paths = []
    seen = set()
    for candidate in ranked:
        for path in candidate.get("graph_paths", []):
            signature = tuple(path.get("relationship_ids", []))
            if not signature or signature in seen:
                continue
            seen.add(signature)
            paths.append(EvidenceGraphPathItem(**path))
            if len(paths) >= 5:
                return EvidenceGraphItem(paths=paths)
    return EvidenceGraphItem(paths=paths)
