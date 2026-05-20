"""Canonical identities shared by all chunk indexes."""
import uuid


_QDRANT_POINT_NAMESPACE = uuid.UUID("9a87e095-8d32-4c89-a470-2fdd60732d3e")


def build_chunk_id(document_scope_id: str, chunk_index: int) -> str:
    """Build the canonical external ID for one chunk."""
    if not document_scope_id:
        raise ValueError("document_scope_id is required")
    if chunk_index < 0:
        raise ValueError("chunk_index must be non-negative")
    return f"{document_scope_id}_chunk_{chunk_index}"


def build_qdrant_point_id(chunk_id: str) -> str:
    """Map a canonical chunk ID to a stable Qdrant-compatible UUID."""
    if not chunk_id:
        raise ValueError("chunk_id is required")
    return str(uuid.uuid5(_QDRANT_POINT_NAMESPACE, chunk_id))