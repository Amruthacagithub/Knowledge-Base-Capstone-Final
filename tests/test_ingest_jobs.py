from uuid import uuid4

import pytest

from backend.database import SessionLocal
from backend.models import Document, IngestJob
from backend.services import ingest_service


def test_successful_ingest_records_completed_job(tmp_path, monkeypatch):
    title = f"job-success-{uuid4()}"
    documents_dir, entry = _entry(tmp_path, title)
    monkeypatch.setattr(
        ingest_service,
        "embed_and_upsert",
        lambda **kwargs: len(kwargs["chunks"]),
    )
    monkeypatch.setattr(
        ingest_service,
        "index_chunks",
        lambda **kwargs: len(kwargs["chunks"]),
    )

    try:
        result = ingest_service.ingest_document_entry(
            entry,
            documents_dir,
            triggered_by_user_id="bhaskar",
        )

        db = SessionLocal()
        try:
            job = db.get(IngestJob, result["ingest_job_id"])
            assert job.status == "succeeded"
            assert job.document_id == result["doc_id"]
            assert job.document_version_id == result["version_id"]
            assert job.chunks_processed == result["chunks_indexed"]
            assert job.vectors_upserted == result["vectors_upserted"]
            assert job.bm25_indexed == result["bm25_indexed"]
            assert job.triggered_by_user_id == "bhaskar"
        finally:
            db.close()
    finally:
        _cleanup(title)


def test_failed_ingest_records_error_and_rolls_back_document(tmp_path, monkeypatch):
    title = f"job-failure-{uuid4()}"
    documents_dir, entry = _entry(tmp_path, title)

    def fail_vector_index(**kwargs):
        raise RuntimeError("synthetic vector failure")

    monkeypatch.setattr(ingest_service, "embed_and_upsert", fail_vector_index)

    with pytest.raises(RuntimeError, match="synthetic vector failure"):
        ingest_service.ingest_document_entry(entry, documents_dir)

    db = SessionLocal()
    try:
        job = db.query(IngestJob).filter_by(title=title).one()
        assert job.status == "failed"
        assert "synthetic vector failure" in job.error_message
        assert db.query(Document).filter_by(title=title).count() == 0
    finally:
        db.delete(job)
        db.commit()
        db.close()


def _entry(tmp_path, title):
    documents_dir = tmp_path / "documents"
    source = documents_dir / "engineering" / f"{title}.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Job fixture\n\nTracked ingestion content.", encoding="utf-8")
    return documents_dir, {
        "path": f"engineering/{title}.md",
        "title": title,
        "department": "Engineering",
        "classification": "public",
        "source_kind": "upload",
    }


def _cleanup(title):
    db = SessionLocal()
    try:
        jobs = db.query(IngestJob).filter_by(title=title).all()
        document = db.query(Document).filter_by(title=title).first()
        for job in jobs:
            db.delete(job)
        if document is not None:
            db.delete(document)
        db.commit()
    finally:
        db.close()