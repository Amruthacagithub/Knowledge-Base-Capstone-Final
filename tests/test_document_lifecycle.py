from datetime import datetime, timezone

from backend.models import Document, DocumentVersion
from backend.services.document_lifecycle import (
    active_upload_entries,
    deactivate_missing_manifest_documents,
)


def test_manifest_reconciliation_deactivates_only_missing_manifest_docs(db_session):
    manifest_document = _document(db_session, "missing-manifest", "manifest")
    upload_document = _document(db_session, "preserved-upload", "upload")
    timestamp = datetime(2026, 7, 25, tzinfo=timezone.utc)

    deactivated = deactivate_missing_manifest_documents(
        db_session,
        active_document_ids=set(),
        deprecated_at=timestamp,
    )

    assert manifest_document.id in deactivated
    assert manifest_document.is_active is False
    assert manifest_document.deprecated_at == timestamp
    assert manifest_document.versions[0].is_current is False
    assert manifest_document.versions[0].effective_to == timestamp
    assert upload_document.is_active is True
    assert upload_document.versions[0].is_current is True


def test_active_upload_entries_are_rebuildable(db_session):
    upload = _document(db_session, "active-upload-entry", "upload")
    inactive_upload = _document(db_session, "inactive-upload-entry", "upload")
    inactive_upload.is_active = False
    db_session.flush()

    entries = active_upload_entries(db_session)

    matching = [entry for entry in entries if entry["path"] == upload.file_path]
    assert matching == [
        {
            "path": upload.file_path,
            "title": upload.title,
            "department": "Engineering",
            "classification": "public",
            "source_kind": "upload",
        }
    ]
    assert all(entry["path"] != inactive_upload.file_path for entry in entries)


def _document(db_session, document_id, source_kind):
    document = Document(
        id=document_id,
        title=document_id,
        department="Engineering",
        classification="public",
        file_path=f"engineering/{document_id}.md",
        source_kind=source_kind,
        is_active=True,
    )
    version = DocumentVersion(
        id=f"{document_id}-v1",
        document=document,
        version_number=1,
        content_hash="a" * 64,
        storage_uri=f"file:///tmp/{document_id}.md",
        file_type="markdown",
        file_size_bytes=10,
        authority_level=50,
        is_current=True,
    )
    db_session.add_all([document, version])
    db_session.flush()
    return document