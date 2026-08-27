from backend.models import Chunk, DocumentVersion
from backend.services import ingest_service


def test_ingest_persists_versioned_chunks_and_reuses_identical_content(
    db_session,
    tmp_path,
    monkeypatch,
):
    documents_dir = tmp_path / "documents"
    source = documents_dir / "engineering" / "runbook.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Runbook\n\nRotate certificates every 90 days.", encoding="utf-8")
    entry = {
        "path": "engineering/runbook.md",
        "title": "Versioned Ingest Runbook",
        "department": "Engineering",
        "classification": "public",
    }
    calls = []

    def capture_index(**kwargs):
        calls.append(kwargs)
        return len(kwargs["chunks"])

    monkeypatch.setattr(ingest_service, "embed_and_upsert", capture_index)
    monkeypatch.setattr(ingest_service, "index_chunks", capture_index)

    first = ingest_service.ingest_document_entry(entry, documents_dir, db=db_session)
    second = ingest_service.ingest_document_entry(entry, documents_dir, db=db_session)

    versions = db_session.query(DocumentVersion).filter_by(document_id=first["doc_id"]).all()
    chunks = db_session.query(Chunk).filter_by(document_version_id=first["version_id"]).all()
    assert first["version_created"] is True
    assert second["version_created"] is False
    assert second["version_id"] == first["version_id"]
    assert len(versions) == 1
    assert len(chunks) == first["chunks_indexed"]
    assert all(call["chunk_scope_id"] == first["version_id"] for call in calls)
    assert all(call["document_version_id"] == first["version_id"] for call in calls)