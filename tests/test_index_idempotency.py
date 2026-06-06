from types import SimpleNamespace

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from backend.services import bm25_index, embedder


class _FakeEmbeddingModel:
    def encode(self, texts, show_progress_bar=False):
        return np.zeros((len(texts), 384), dtype=float)


class _FakeQdrantClient:
    def __init__(self):
        self.points = {}

    def scroll(self, *, scroll_filter=None, **kwargs):
        doc_id = scroll_filter.must[0].match.value if scroll_filter else None
        records = [
            SimpleNamespace(id=point_id, payload=point.payload)
            for point_id, point in self.points.items()
            if doc_id is None or point.payload["doc_id"] == doc_id
        ]
        return records, None

    def upsert(self, *, points, **kwargs):
        for point in points:
            self.points[point.id] = point

    def delete(self, *, points_selector, **kwargs):
        for point_id in points_selector.points:
            self.points.pop(point_id, None)


def test_qdrant_reingest_reuses_ids_and_removes_stale_chunks(monkeypatch):
    client = _FakeQdrantClient()
    monkeypatch.setattr(embedder, "get_embedding_model", lambda: _FakeEmbeddingModel())
    monkeypatch.setattr(embedder, "get_qdrant_client", lambda: client)

    chunks = [{"text": "first"}, {"text": "second"}]
    _embed(chunks)
    first_ids = set(client.points)

    _embed(chunks)
    assert set(client.points) == first_ids

    _embed(chunks[:1])
    assert len(client.points) == 1
    assert set(client.points).issubset(first_ids)


def test_qdrant_local_mode_replacement_is_idempotent(monkeypatch):
    collection_name = "trust_rag_idempotency"
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    monkeypatch.setattr(embedder, "QDRANT_COLLECTION", collection_name)
    monkeypatch.setattr(embedder, "get_embedding_model", lambda: _FakeEmbeddingModel())
    monkeypatch.setattr(embedder, "get_qdrant_client", lambda: client)

    chunks = [{"text": "first"}, {"text": "second"}]
    _embed(chunks)
    first_records, _ = client.scroll(collection_name, limit=10)
    first_ids = {record.id for record in first_records}

    _embed(chunks)
    repeated_records, _ = client.scroll(collection_name, limit=10)
    assert {record.id for record in repeated_records} == first_ids

    _embed(chunks[:1])
    final_records, _ = client.scroll(collection_name, limit=10)
    assert len(final_records) == 1
    assert {record.id for record in final_records}.issubset(first_ids)


def test_qdrant_manifest_sync_prunes_removed_documents(monkeypatch):
    collection_name = "trust_rag_manifest_sync"
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    monkeypatch.setattr(embedder, "QDRANT_COLLECTION", collection_name)
    monkeypatch.setattr(embedder, "get_embedding_model", lambda: _FakeEmbeddingModel())
    monkeypatch.setattr(embedder, "get_qdrant_client", lambda: client)

    _embed([{"text": "first"}])
    embedder.embed_and_upsert(
        chunks=[{"text": "removed"}],
        doc_id="document-2",
        doc_title="Document Two",
        department="Engineering",
        classification="public",
    )

    removed = embedder.prune_points_for_missing_documents({"document-1"})
    records, _ = client.scroll(collection_name, limit=10, with_payload=True)

    assert removed == 1
    assert {record.payload["doc_id"] for record in records} == {"document-1"}


def test_bm25_reingest_removes_stale_chunks(monkeypatch, tmp_path):
    monkeypatch.setattr(bm25_index, "BM25_INDEX_DIR", tmp_path / "index")

    _index([{"text": "first"}, {"text": "second"}])
    _index([{"text": "first"}])

    with bm25_index.get_bm25_index().searcher() as searcher:
        assert searcher.doc_count() == 1


def test_legacy_vector_payload_gets_canonical_chunk_id():
    hit = SimpleNamespace(
        id="legacy-point",
        score=0.75,
        payload={
            "text": "legacy chunk",
            "doc_id": "document-1",
            "doc_title": "Document One",
            "department": "Engineering",
            "classification": "public",
            "chunk_index": 2,
        },
    )

    result = embedder._vector_hit_to_result(hit)

    assert result["chunk_id"] == "document-1_chunk_2"


def _embed(chunks):
    return embedder.embed_and_upsert(
        chunks=chunks,
        doc_id="document-1",
        doc_title="Document One",
        department="Engineering",
        classification="public",
    )


def _index(chunks):
    return bm25_index.index_chunks(
        chunks=chunks,
        doc_id="document-1",
        doc_title="Document One",
        department="Engineering",
        classification="public",
    )