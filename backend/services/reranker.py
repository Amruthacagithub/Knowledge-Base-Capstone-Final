"""Cross-encoder reranker — re-scores query-chunk pairs for better precision."""

from sentence_transformers import CrossEncoder
from backend.config import MODEL_DEVICE, RERANKER_MODEL

# ── Singleton ──
_reranker = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        print(f"  Loading reranker: {RERANKER_MODEL} on {MODEL_DEVICE} ...")
        _reranker = CrossEncoder(RERANKER_MODEL, device=MODEL_DEVICE)
    return _reranker


def _canonical_doc_key(chunk: dict) -> str:
    """Group markdown + PDF variants (e.g. Leave Policy vs Leave Policy (PDF))."""
    title = (chunk.get("doc_title") or "").strip()
    if title.lower().endswith("(pdf)"):
        title = title[:-5].rstrip()
    title = title.lower()
    if title:
        return title
    return (chunk.get("doc_id") or "").lower()


def diversify_by_document(candidates: list[dict], top_n: int = 8, max_per_doc: int = 1) -> list[dict]:
    """Prefer one chunk per logical document so citations span different sources."""
    picked: list[dict] = []
    counts: dict[str, int] = {}

    for c in candidates:
        key = _canonical_doc_key(c)
        if counts.get(key, 0) >= max_per_doc:
            continue
        picked.append(c)
        counts[key] = counts.get(key, 0) + 1
        if len(picked) >= top_n:
            break

    return picked


def rerank(query: str, candidates: list[dict], top_n: int = 8) -> list[dict]:
    """
    Re-score candidates using a cross-encoder model.

    Args:
        query: The user's search query.
        candidates: List of chunk dicts from hybrid search.
        top_n: Number of top results to return.

    Returns:
        Re-ranked list of chunk dicts with 'rerank_score' field.
    """
    if not candidates:
        return []

    reranker = get_reranker()

    # Build (query, passage) pairs
    pairs = [(query, c["text"]) for c in candidates]

    # Score all pairs
    scores = reranker.predict(pairs)

    # Attach scores to candidates
    for candidate, score in zip(candidates, scores):
        candidate["rerank_score"] = float(score)

    # Sort by rerank score descending
    reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)

    # Over-fetch then diversify so the LLM sees distinct documents
    pool = reranked[: max(top_n * 3, top_n)]
    return diversify_by_document(pool, top_n=top_n, max_per_doc=1)
