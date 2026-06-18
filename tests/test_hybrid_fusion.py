from backend.services.retriever import _reciprocal_rank_fusion


def _result(source: str, *, chunk_id: str, chunk_index: int | None) -> dict:
    result = {
        "chunk_id": chunk_id,
        "doc_id": "doc-1",
        "doc_title": "Document One",
        "department": "Engineering",
        "classification": "public",
        "text": "The same logical chunk returned by both retrieval methods.",
        "score": 1.0,
        "source": source,
    }
    if chunk_index is not None:
        result["chunk_index"] = chunk_index
    return result


def test_rrf_merges_matching_vector_and_bm25_chunk_ids():
    vector_result = _result("vector", chunk_id="doc-1_chunk_0", chunk_index=0)
    bm25_result = _result("bm25", chunk_id="doc-1_chunk_0", chunk_index=None)

    fused = _reciprocal_rank_fusion([vector_result], [bm25_result])

    assert len(fused) == 1
    assert fused[0]["chunk_id"] == "doc-1_chunk_0"
    assert fused[0]["vec_rrf"] > 0
    assert fused[0]["bm25_rrf"] > 0


def test_rrf_keeps_distinct_chunk_ids_separate():
    vector_result = _result("vector", chunk_id="doc-1_chunk_0", chunk_index=0)
    bm25_result = _result("bm25", chunk_id="doc-1_chunk_1", chunk_index=None)

    fused = _reciprocal_rank_fusion([vector_result], [bm25_result])

    assert {result["chunk_id"] for result in fused} == {
        "doc-1_chunk_0",
        "doc-1_chunk_1",
    }