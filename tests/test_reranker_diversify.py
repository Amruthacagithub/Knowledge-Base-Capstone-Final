from backend.services.reranker import _canonical_doc_key, diversify_by_document


def test_canonical_doc_key_strips_pdf_suffix():
    chunk = {"doc_title": "Leave Policy (PDF)", "doc_id": "abc"}
    assert _canonical_doc_key(chunk) == "leave policy"


def test_diversify_one_per_document():
    candidates = [
        {"doc_title": "Leave Policy", "doc_id": "1", "rerank_score": 0.9},
        {"doc_title": "Leave Policy (PDF)", "doc_id": "2", "rerank_score": 0.85},
        {"doc_title": "Employee Handbook", "doc_id": "3", "rerank_score": 0.8},
    ]
    out = diversify_by_document(candidates, top_n=3, max_per_doc=1)
    assert len(out) == 2
    titles = {_canonical_doc_key(c) for c in out}
    assert "leave policy" in titles
    assert "employee handbook" in titles
