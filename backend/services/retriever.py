"""
Hybrid retriever — combines vector search and BM25 keyword search.
"""
from backend.config import VECTOR_SEARCH_ENABLED
from backend.services.bm25_index import keyword_search
from backend.services.permissions import build_permission_filter, filter_bm25_results
from backend.services.auth import UserContext
from backend.services.query_router import classify_query, alpha_for_query_type

if VECTOR_SEARCH_ENABLED:
    from backend.services.embedder import vector_search


def hybrid_search(
    query: str,
    user_ctx: UserContext,
    department_filter: str | None = None,
    alpha: float | None = None,
    top_k: int = 20,
) -> tuple[list[dict], str]:
    """
    Perform hybrid search combining vector and BM25 results.

    Args:
        query: The user's search query.
        user_ctx: Authenticated user context.
        department_filter: Optional department to filter by.
        alpha: Weight for vector search (1-alpha for BM25).
        top_k: Number of results to return.

    Returns:
        Tuple of (fused chunk results, query_type).
    """
    query_type = classify_query(query)
    if alpha is None:
        alpha = 0.0 if not VECTOR_SEARCH_ENABLED else alpha_for_query_type(query_type)

    vec_results: list[dict] = []
    if VECTOR_SEARCH_ENABLED:
        qdrant_filter = build_permission_filter(user_ctx)
        vec_results = vector_search(
            query=query,
            qdrant_filter=qdrant_filter,
            top_k=top_k,
        )

    # BM25 keyword search
    bm25_results = keyword_search(
        query=query,
        department_filter=department_filter,
        top_k=top_k,
    )

    # Post-filter BM25 results for permissions
    bm25_results = filter_bm25_results(bm25_results, user_ctx)

    # Normalize scores
    vec_results = _normalize_scores(vec_results)
    bm25_results = _normalize_scores(bm25_results)

    # Fuse results using reciprocal rank fusion
    fused = _reciprocal_rank_fusion(vec_results, bm25_results, alpha=alpha)

    # Department filter (if specified, apply to fused results)
    if department_filter:
        fused = [r for r in fused if r["department"] == department_filter]

    return fused[:top_k], query_type


def _normalize_scores(results: list[dict]) -> list[dict]:
    """Normalize scores to [0, 1] range."""
    if not results:
        return results
    max_score = max(r["score"] for r in results)
    min_score = min(r["score"] for r in results)
    score_range = max_score - min_score

    for r in results:
        if score_range > 0:
            r["score"] = (r["score"] - min_score) / score_range
        else:
            r["score"] = 1.0

    return results


def _reciprocal_rank_fusion(
    vec_results: list[dict],
    bm25_results: list[dict],
    alpha: float = 0.7,
    k: int = 60,
) -> list[dict]:
    """
    Fuse two ranked lists using Reciprocal Rank Fusion (RRF).

    Each result gets a score: alpha * (1 / (k + rank_vec)) + (1-alpha) * (1 / (k + rank_bm25))
    where rank is the position in each list (0-indexed).
    """
    # Build lookup by canonical chunk identity to deduplicate.
    combined = {}

    for rank, r in enumerate(vec_results):
        key = _chunk_key(r)
        if key not in combined:
            combined[key] = {**r, "vec_rrf": 0.0, "bm25_rrf": 0.0}
        combined[key]["vec_rrf"] = 1.0 / (k + rank)

    for rank, r in enumerate(bm25_results):
        key = _chunk_key(r)
        if key not in combined:
            combined[key] = {**r, "vec_rrf": 0.0, "bm25_rrf": 0.0}
        combined[key]["bm25_rrf"] = 1.0 / (k + rank)

    # Compute final fused score
    for key, r in combined.items():
        r["score"] = alpha * r["vec_rrf"] + (1 - alpha) * r["bm25_rrf"]

    # Sort by fused score descending
    fused = sorted(combined.values(), key=lambda x: x["score"], reverse=True)

    return fused


def _chunk_key(result: dict) -> tuple[str, str, str]:
    """Return one stable identity for a chunk from either retrieval backend."""
    chunk_id = result.get("chunk_id")
    if chunk_id:
        return ("chunk", str(chunk_id), "")

    chunk_index = result.get("chunk_index")
    if chunk_index is not None:
        return ("legacy", str(result["doc_id"]), str(int(chunk_index)))

    return ("legacy-text", str(result["doc_id"]), result["text"])
