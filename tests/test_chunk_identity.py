import pytest

from backend.services.chunk_identity import build_chunk_id, build_qdrant_point_id


def test_chunk_and_point_ids_are_stable():
    chunk_id = build_chunk_id("document-1", 3)

    assert chunk_id == "document-1_chunk_3"
    assert build_qdrant_point_id(chunk_id) == "560efae3-651c-57a1-8f9a-fc90c1b8c56b"
    assert build_qdrant_point_id(chunk_id) != build_qdrant_point_id(
        build_chunk_id("document-1", 4)
    )


@pytest.mark.parametrize(
    ("document_scope_id", "chunk_index"),
    [("", 0), ("document-1", -1)],
)
def test_invalid_chunk_identity_inputs_are_rejected(document_scope_id, chunk_index):
    with pytest.raises(ValueError):
        build_chunk_id(document_scope_id, chunk_index)