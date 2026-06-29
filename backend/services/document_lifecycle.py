"""Source-aware document activation and corpus reconciliation."""
from datetime import datetime, timezone

from backend.models import Document


def active_upload_entries(db) -> list[dict]:
    """Return database-owned uploads that must survive a manifest rebuild."""
    documents = (
        db.query(Document)
        .filter(
            Document.source_kind == "upload",
            Document.is_active.is_(True),
        )
        .order_by(Document.file_path)
        .all()
    )
    return [
        {
            "path": document.file_path,
            "title": document.title,
            "department": document.department,
            "classification": document.classification,
            "source_kind": "upload",
        }
        for document in documents
    ]


def deactivate_missing_manifest_documents(
    db,
    active_document_ids: set[str],
    *,
    deprecated_at: datetime | None = None,
) -> set[str]:
    """Deactivate manifest-owned documents absent from a successful full sync."""
    timestamp = deprecated_at or datetime.now(timezone.utc)
    candidates = (
        db.query(Document)
        .filter(
            Document.source_kind == "manifest",
            Document.is_active.is_(True),
        )
        .all()
    )
    deactivated_ids = set()
    for document in candidates:
        document_id = str(document.id)
        if document_id in active_document_ids:
            continue
        document.is_active = False
        document.deprecated_at = timestamp
        for version in document.versions:
            if version.is_current:
                version.is_current = False
                version.effective_to = version.effective_to or timestamp
        deactivated_ids.add(document_id)
    return deactivated_ids