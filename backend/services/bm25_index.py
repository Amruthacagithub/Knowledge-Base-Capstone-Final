"""
BM25 keyword search using Whoosh.
"""
from pathlib import Path
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, NUMERIC
from whoosh.qparser import MultifieldParser
from whoosh import scoring

from backend.config import BM25_INDEX_DIR
from backend.services.chunk_identity import build_chunk_id


# ── Whoosh Schema ──
SCHEMA = Schema(
    chunk_id=ID(stored=True, unique=True),
    doc_id=ID(stored=True),
    document_version_id=ID(stored=True),
    doc_title=TEXT(stored=True),
    department=ID(stored=True),
    classification=ID(stored=True),
    text=TEXT(stored=True),
    page_start=NUMERIC(stored=True),
    page_end=NUMERIC(stored=True),
    file_type=ID(stored=True),
)


def ensure_index_dir():
    """Create the index directory if it doesn't exist."""
    BM25_INDEX_DIR.mkdir(parents=True, exist_ok=True)


def create_bm25_index():
    """Create a fresh Whoosh index (overwrites existing)."""
    ensure_index_dir()
    ix = create_in(str(BM25_INDEX_DIR), SCHEMA)
    print(f"  Created BM25 index at: {BM25_INDEX_DIR}")
    return ix


def get_bm25_index():
    """Open existing index or create a new one."""
    ensure_index_dir()
    if exists_in(str(BM25_INDEX_DIR)):
        ix = open_dir(str(BM25_INDEX_DIR))
        if "document_version_id" in ix.schema.names():
            return ix
    return create_bm25_index()


def _normalize_chunks(chunks: list) -> list[dict]:
    out = []
    for c in chunks:
        if isinstance(c, dict):
            out.append(c)
        else:
            out.append({"text": c, "page_start": 1, "page_end": 1})
    return out


def index_chunks(
    chunks: list,
    doc_id: str,
    doc_title: str,
    department: str,
    classification: str,
    file_type: str = "markdown",
    chunk_scope_id: str | None = None,
    document_version_id: str | None = None,
) -> int:
    """
    Index text chunks into BM25.

    Returns:
        Number of chunks indexed.
    """
    ix = get_bm25_index()
    writer = ix.writer()
    writer.delete_by_term("doc_id", doc_id)
    scope_id = chunk_scope_id or doc_id

    for i, chunk in enumerate(_normalize_chunks(chunks)):
        chunk_id = build_chunk_id(scope_id, i)
        writer.add_document(
            chunk_id=chunk_id,
            doc_id=doc_id,
            document_version_id=document_version_id or "",
            doc_title=doc_title,
            department=department,
            classification=classification,
            text=chunk["text"],
            page_start=chunk.get("page_start", 1),
            page_end=chunk.get("page_end", 1),
            file_type=file_type,
        )

    writer.commit()
    return len(chunks)


def keyword_search(
    query: str,
    department_filter: str | None = None,
    top_k: int = 20,
) -> list[dict]:
    """
    Search BM25 index for keyword matches.

    Permission filtering is done post-retrieval since Whoosh doesn't support
    complex role-based filters natively.

    Returns:
        List of dicts with text, doc_id, doc_title, department, score.
    """
    ix = get_bm25_index()
    parser = MultifieldParser(["text", "doc_title"], schema=ix.schema)
    parsed_query = parser.parse(query)

    results = []
    with ix.searcher(weighting=scoring.BM25F()) as searcher:
        hits = searcher.search(parsed_query, limit=top_k * 2)  # over-fetch for filtering

        for hit in hits:
            # Department filter
            if department_filter and hit["department"] != department_filter:
                continue

            results.append({
                "chunk_id": hit["chunk_id"],
                "text": hit["text"],
                "doc_id": hit["doc_id"],
                "document_version_id": hit.get("document_version_id") or None,
                "doc_title": str(hit["doc_title"]),
                "department": hit["department"],
                "classification": hit.get("classification", "public"),
                "page_start": int(hit.get("page_start") or 1),
                "page_end": int(hit.get("page_end") or 1),
                "file_type": hit.get("file_type") or "markdown",
                "score": hit.score,
                "source": "bm25",
            })

            if len(results) >= top_k:
                break

    return results
