"""
Embedding service — encodes text chunks and upserts into Qdrant.
"""
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, PayloadSchemaType, PointIdsList,
)

from backend.config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
    MODEL_DEVICE,
)
from backend.services.chunk_identity import build_chunk_id, build_qdrant_point_id
from backend.services.rbac import department_to_role

# ── Singletons (loaded once, reused) ──
_model = None
_client = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"  Loading embedding model: {EMBEDDING_MODEL} on {MODEL_DEVICE} ...")
        _model = SentenceTransformer(EMBEDDING_MODEL, device=MODEL_DEVICE)
    return _model


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        import os
        qdrant_path = os.getenv("QDRANT_PATH", "")
        if QDRANT_URL:
            _client = QdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY or None,
                check_compatibility=False,
            )
            label = QDRANT_URL if len(QDRANT_URL) <= 48 else f"{QDRANT_URL[:45]}…"
            print(f"  Qdrant client: cloud ({label})")
        elif qdrant_path or QDRANT_HOST in {":memory:", "memory"} or QDRANT_HOST.startswith("./") or QDRANT_HOST.startswith("qdrant_"):
            storage_path = qdrant_path or QDRANT_HOST
            _client = QdrantClient(path=storage_path) if storage_path != ":memory:" else QdrantClient(":memory:")
            print(f"  Qdrant client: embedded ({storage_path})")
        else:
            _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            print(f"  Qdrant client: {QDRANT_HOST}:{QDRANT_PORT}")
    return _client



def ensure_payload_indexes():
    """Keyword indexes required for RBAC filters on Qdrant Cloud."""
    client = get_qdrant_client()
    for field in ("access_roles", "department", "classification"):
        try:
            client.create_payload_index(
                collection_name=QDRANT_COLLECTION,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD,
            )
            print(f"  Created payload index: {field}")
        except Exception as exc:
            msg = str(exc).lower()
            if "already exists" in msg or "already has" in msg:
                continue
            print(f"  Payload index {field}: {exc}")


def ensure_collection():
    """Create the Qdrant collection if it doesn't exist."""
    client = get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in collections:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )
        print(f"  Created Qdrant collection: {QDRANT_COLLECTION}")
    else:
        print(f"  Qdrant collection already exists: {QDRANT_COLLECTION}")
    ensure_payload_indexes()


def _chunk_texts(chunks: list) -> list[dict]:
    """Normalize chunks as list of dicts with text and page fields."""
    out = []
    for c in chunks:
        if isinstance(c, dict):
            out.append(c)
        else:
            out.append({"text": c, "page_start": 1, "page_end": 1})
    return out


def embed_and_upsert(
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
    Embed text chunks and upsert them into Qdrant.

    Returns:
        Number of points upserted.
    """
    chunk_dicts = _chunk_texts(chunks)
    if not chunk_dicts:
        return 0

    model = get_embedding_model()
    client = get_qdrant_client()

    texts = [c["text"] for c in chunk_dicts]
    vectors = model.encode(texts, show_progress_bar=False).tolist()
    existing_point_ids = _point_ids_for_document(client, doc_id)

    # Build access_roles list based on classification + department
    if classification == "public":
        access_roles = ["Employee", "HR", "Engineer", "Sales", "Admin"]
    else:
        # restricted: only the department's role + admin
        access_roles = [department_to_role(department), "Admin"]

    # Create points
    points = []
    scope_id = chunk_scope_id or doc_id
    for i, (chunk, vector) in enumerate(zip(chunk_dicts, vectors)):
        chunk_id = build_chunk_id(scope_id, i)
        point_id = build_qdrant_point_id(chunk_id)
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "chunk_id": chunk_id,
                    "text": chunk["text"],
                    "doc_id": doc_id,
                    "document_version_id": document_version_id,
                    "doc_title": doc_title,
                    "department": department,
                    "classification": classification,
                    "access_roles": access_roles,
                    "chunk_index": i,
                    "page_start": chunk.get("page_start", 1),
                    "page_end": chunk.get("page_end", 1),
                    "file_type": file_type,
                },
            )
        )

    # Upsert in batches of 64
    batch_size = 64
    for start in range(0, len(points), batch_size):
        batch = points[start : start + batch_size]
        client.upsert(collection_name=QDRANT_COLLECTION, points=batch, wait=True)

    new_point_ids = {point.id for point in points}
    stale_point_ids = list(existing_point_ids - new_point_ids)
    if stale_point_ids:
        client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=PointIdsList(points=stale_point_ids),
            wait=True,
        )

    return len(points)


def _point_ids_for_document(client: QdrantClient, doc_id: str) -> set:
    """Read all current point IDs for a logical document."""
    point_ids = set()
    offset = None
    while True:
        records, offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id),
                    )
                ]
            ),
            limit=256,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        point_ids.update(record.id for record in records)
        if offset is None:
            return point_ids


def prune_points_for_missing_documents(active_doc_ids: set[str]) -> int:
    """Delete points outside a fully ingested corpus manifest."""
    client = get_qdrant_client()
    stale_point_ids = []
    offset = None

    while True:
        records, offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for record in records:
            payload = record.payload or {}
            doc_id = payload.get("doc_id")
            if doc_id and str(doc_id) not in active_doc_ids:
                stale_point_ids.append(record.id)
        if offset is None:
            break

    if stale_point_ids:
        client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=PointIdsList(points=stale_point_ids),
            wait=True,
        )
    return len(stale_point_ids)


def vector_search(
    query: str,
    qdrant_filter: Filter | None = None,
    top_k: int = 20,
) -> list[dict]:
    """
    Search Qdrant for chunks similar to the query.

    Returns:
        List of dicts with text, doc_id, doc_title, department, score.
    """
    model = get_embedding_model()
    client = get_qdrant_client()

    query_vector = model.encode(query).tolist()

    results = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        query_filter=qdrant_filter,
        limit=top_k,
        with_payload=True,
    )

    return [_vector_hit_to_result(hit) for hit in results.points]


def _vector_hit_to_result(hit) -> dict:
    """Convert a Qdrant hit, including payloads from the pre-canonical index."""
    payload = hit.payload
    if payload is None:
        raise ValueError(f"Qdrant point {hit.id} has no payload")

    chunk_index = int(payload.get("chunk_index", 0))
    chunk_id = payload.get("chunk_id") or build_chunk_id(
        str(payload["doc_id"]),
        chunk_index,
    )
    return {
        "chunk_id": chunk_id,
        "text": payload["text"],
        "doc_id": payload["doc_id"],
        "document_version_id": payload.get("document_version_id"),
        "doc_title": payload["doc_title"],
        "department": payload["department"],
        "classification": payload.get("classification", "public"),
        "chunk_index": chunk_index,
        "page_start": payload.get("page_start", 1),
        "page_end": payload.get("page_end", 1),
        "file_type": payload.get("file_type", "markdown"),
        "score": hit.score,
        "source": "vector",
    }
