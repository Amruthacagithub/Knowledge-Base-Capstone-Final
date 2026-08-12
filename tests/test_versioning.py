from datetime import datetime, timezone

from backend.models import Chunk, Document, DocumentVersion
from backend.services.versioning import ensure_document_version


def test_identical_content_reuses_document_version(db_session, tmp_path):
    document = _document(db_session, "versioning-identical")
    source = tmp_path / "policy.md"
    source.write_text("Policy version one.", encoding="utf-8")
    chunks = [{"text": "Policy version one.", "page_start": 1, "page_end": 1}]

    first, first_created = ensure_document_version(
        db_session,
        document=document,
        file_path=source,
        file_type="markdown",
        chunks=chunks,
    )
    second, second_created = ensure_document_version(
        db_session,
        document=document,
        file_path=source,
        file_type="markdown",
        chunks=chunks,
    )

    assert first_created is True
    assert second_created is False
    assert second.id == first.id
    assert db_session.query(DocumentVersion).filter_by(document_id=document.id).count() == 1
    assert db_session.query(Chunk).filter_by(document_version_id=first.id).count() == 1


def test_changed_content_supersedes_current_version(db_session, tmp_path):
    document = _document(db_session, "versioning-change")
    source = tmp_path / "runbook.md"
    source.write_text("Rotate certificates every 12 months.", encoding="utf-8")
    first_effective = datetime(2025, 1, 1, tzinfo=timezone.utc)
    second_effective = datetime(2026, 1, 1, tzinfo=timezone.utc)

    first, _ = ensure_document_version(
        db_session,
        document=document,
        file_path=source,
        file_type="markdown",
        chunks=[{"text": "Rotate certificates every 12 months."}],
        effective_from=first_effective,
    )
    source.write_text("Rotate certificates every 90 days.", encoding="utf-8")
    second, created = ensure_document_version(
        db_session,
        document=document,
        file_path=source,
        file_type="markdown",
        chunks=[{"text": "Rotate certificates every 90 days."}],
        effective_from=second_effective,
    )

    assert created is True
    assert second.version_number == 2
    assert second.is_current is True
    assert first.is_current is False
    assert first.superseded_by_id == second.id
    assert first.effective_to == second_effective
    assert [chunk.id for chunk in second.chunks] == [f"{second.id}_chunk_0"]


def _document(db_session, document_id):
    document = Document(
        id=document_id,
        title=document_id,
        department="Engineering",
        classification="public",
        file_path=f"engineering/{document_id}.md",
    )
    db_session.add(document)
    db_session.flush()
    return document