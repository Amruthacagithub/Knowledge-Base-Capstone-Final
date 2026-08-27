from backend.models import ExtractionRun
from backend.services import ingest_service


def test_engineering_ingest_runs_opt_in_extraction(db_session, tmp_path, monkeypatch):
    documents_dir, entry = _entry(tmp_path, "Engineering")
    captured_versions = []
    _mock_indexes(monkeypatch)
    monkeypatch.setattr(ingest_service, "EVIDENCE_EXTRACTION_ENABLED", True)
    monkeypatch.setattr(
        ingest_service,
        "extract_and_store_version",
        lambda db, version_id: captured_versions.append(version_id)
        or {"extraction_run_id": "run-1", "claims": 2},
    )

    result = ingest_service.ingest_document_entry(entry, documents_dir, db=db_session)

    assert captured_versions == [result["version_id"]]
    assert result["evidence_extraction"] == {
        "status": "succeeded",
        "extraction_run_id": "run-1",
        "claims": 2,
    }


def test_non_engineering_ingest_does_not_extract(db_session, tmp_path, monkeypatch):
    documents_dir, entry = _entry(tmp_path, "HR")
    _mock_indexes(monkeypatch)
    monkeypatch.setattr(ingest_service, "EVIDENCE_EXTRACTION_ENABLED", True)
    monkeypatch.setattr(
        ingest_service,
        "extract_and_store_version",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    result = ingest_service.ingest_document_entry(entry, documents_dir, db=db_session)

    assert result["evidence_extraction"] == {"status": "disabled"}


def test_extraction_failure_does_not_rollback_core_ingest(
    db_session,
    tmp_path,
    monkeypatch,
):
    documents_dir, entry = _entry(tmp_path, "Engineering")
    _mock_indexes(monkeypatch)
    monkeypatch.setattr(ingest_service, "EVIDENCE_EXTRACTION_ENABLED", True)

    def fail_extraction(db, version_id):
        raise RuntimeError("synthetic extraction failure")

    monkeypatch.setattr(ingest_service, "extract_and_store_version", fail_extraction)

    result = ingest_service.ingest_document_entry(entry, documents_dir, db=db_session)

    run = db_session.get(ExtractionRun, result["evidence_extraction"]["extraction_run_id"])
    assert result["doc_id"]
    assert result["version_id"]
    assert result["evidence_extraction"]["status"] == "failed"
    assert run.status == "failed"
    assert "synthetic extraction failure" in run.error_message


def _entry(tmp_path, department):
    documents_dir = tmp_path / "documents"
    relative_path = f"{department.lower()}/evidence.md"
    source = documents_dir / relative_path
    source.parent.mkdir(parents=True)
    source.write_text(
        "Incident INC-5023 affected Billing Service.",
        encoding="utf-8",
    )
    return documents_dir, {
        "path": relative_path,
        "title": f"{department} Evidence Fixture",
        "department": department,
        "classification": "public",
        "source_kind": "upload",
    }


def _mock_indexes(monkeypatch):
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