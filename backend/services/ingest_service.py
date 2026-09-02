"""
Single-document ingestion — shared by CLI ingest and upload API.
"""
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.config import EVIDENCE_EXTRACTION_ENABLED, VECTOR_SEARCH_ENABLED
from backend.database import SessionLocal
from backend.models import Document, IngestJob
from backend.services.parser import parse_document
from backend.services.chunker import chunk_document_segments
from backend.services.bm25_index import index_chunks
from backend.services.evidence_store import (
    extract_and_store_version,
    record_failed_extraction,
)
from backend.services.versioning import ensure_document_version


_VERSIONED_PATH = re.compile(
    r"^(?P<base>.+)_v(?P<version>\d+)\.(?P<ext>md|pdf)$",
    re.IGNORECASE,
)
_EFFECTIVE_FROM = re.compile(
    r"\*\*Effective:\*\*\s*(?P<start>\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def file_type_from_path(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    return "markdown"


def ingest_document_entry(
    entry: dict,
    documents_dir: Path,
    db=None,
    *,
    reindex_existing: bool = True,
    triggered_by_user_id: str | None = None,
    source_file_path: Path | None = None,
) -> dict:
    """
    Parse, chunk, embed, and BM25-index one manifest entry.

    entry keys: path, title, department, classification

    Returns:
        {doc_id, title, chunks_indexed, file_type}
    """
    file_path = source_file_path or documents_dir / entry["path"]
    source_path = str(entry.get("_source_path") or entry["path"])
    if source_file_path is None and source_path != entry["path"]:
        file_path = documents_dir / source_path
    title = entry["title"]
    department = entry["department"]
    classification = entry["classification"]
    source_kind = entry.get("source_kind", "manifest")
    file_type = file_type_from_path(file_path)

    if source_kind not in {"manifest", "upload"}:
        raise ValueError(f"Unsupported source_kind: {source_kind}")

    own_db = db is None
    if own_db:
        db = SessionLocal()

    job = IngestJob(
        id=str(uuid.uuid4()),
        source_path=str(entry["path"]),
        title=title,
        source_kind=source_kind,
        status="running",
        triggered_by_user_id=triggered_by_user_id,
    )
    db.add(job)
    db.commit()

    try:
        chunks = _parse_chunks(file_path)
        document = _get_or_create_document(
            db,
            entry,
            source_kind=source_kind,
            reindex_existing=reindex_existing,
        )
        db.flush()

        version, version_created = ensure_document_version(
            db,
            document=document,
            file_path=file_path,
            file_type=file_type,
            chunks=chunks,
            uploaded_by_user_id=triggered_by_user_id,
            storage_uri=entry.get("storage_uri"),
            effective_from=_parse_effective_from(file_path),
        )
        doc_id = str(document.id)
        version_id = str(version.id)

        if VECTOR_SEARCH_ENABLED:
            from backend.services.embedder import embed_and_upsert

            n_vectors = embed_and_upsert(
                chunks=chunks,
                doc_id=doc_id,
                doc_title=title,
                department=department,
                classification=classification,
                file_type=file_type,
                chunk_scope_id=version_id,
                document_version_id=version_id,
            )
        else:
            n_vectors = 0
        n_bm25 = index_chunks(
            chunks=chunks,
            doc_id=doc_id,
            doc_title=title,
            department=department,
            classification=classification,
            file_type=file_type,
            chunk_scope_id=version_id,
            document_version_id=version_id,
        )

        job.document_id = doc_id
        job.document_version_id = version_id
        job.status = "succeeded"
        job.completed_at = datetime.now(timezone.utc)
        job.chunks_processed = len(chunks)
        job.vectors_upserted = n_vectors
        job.bm25_indexed = n_bm25
        db.commit()

        extraction_result = _extract_evidence(db, department, version_id)

        return {
            "ingest_job_id": job.id,
            "doc_id": doc_id,
            "version_id": version_id,
            "version_number": version.version_number,
            "version_created": version_created,
            "title": title,
            "chunks_indexed": len(chunks),
            "vectors_upserted": n_vectors,
            "bm25_indexed": n_bm25,
            "file_type": file_type,
            "evidence_extraction": extraction_result,
        }
    except Exception as exc:
        db.rollback()
        _record_failed_job(db, job.id, exc)
        raise
    finally:
        if own_db:
            db.close()


def _parse_chunks(file_path: Path) -> list[dict]:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    segments = parse_document(file_path)
    if not segments:
        raise ValueError(f"No text extracted from {file_path}")
    chunks = chunk_document_segments(segments)
    if not chunks:
        raise ValueError(f"No chunks produced from {file_path}")
    return chunks


def _get_or_create_document(db, entry, *, source_kind, reindex_existing):
    canonical_path = str(entry["path"])
    existing = (
        db.query(Document)
        .filter(Document.file_path == canonical_path)
        .first()
    )
    if existing is None:
        legacy = _find_legacy_versioned_document(db, canonical_path)
        if legacy is not None:
            legacy.file_path = canonical_path
            if reindex_existing:
                legacy.title = entry["title"]
                legacy.department = entry["department"]
                legacy.classification = entry["classification"]
                legacy.source_kind = source_kind
                legacy.is_active = True
                legacy.deprecated_at = None
            return legacy
        document = Document(
            id=str(uuid.uuid4()),
            title=entry["title"],
            department=entry["department"],
            classification=entry["classification"],
            file_path=canonical_path,
            source_kind=source_kind,
            is_active=True,
        )
        db.add(document)
        return document
    if reindex_existing:
        existing.title = entry["title"]
        existing.department = entry["department"]
        existing.classification = entry["classification"]
        existing.source_kind = source_kind
        existing.is_active = True
        existing.deprecated_at = None
    return existing


def canonicalize_manifest_entry(entry: dict) -> dict:
    """Map versioned manifest paths onto one canonical document identity."""
    path = str(entry["path"]).replace("\\", "/")
    match = _VERSIONED_PATH.match(path)
    if match is None:
        return dict(entry)
    canonical_path = f"{match.group('base')}.{match.group('ext')}"
    base_name = match.group("base").split("/")[-1].replace("_", " ").title()
    return {
        **entry,
        "path": canonical_path,
        "title": base_name,
        "_source_path": path,
    }


def _find_legacy_versioned_document(db, canonical_path: str):
    stem, _, suffix = canonical_path.rpartition(".")
    if not stem:
        return None
    pattern = f"{stem}_v%.{suffix}"
    return (
        db.query(Document)
        .filter(Document.file_path.like(pattern))
        .order_by(Document.file_path)
        .first()
    )


def _parse_effective_from(file_path: Path) -> datetime | None:
    if file_path.suffix.lower() != ".md":
        return None
    try:
        text = file_path.read_text(encoding="utf-8")[:800]
    except OSError:
        return None
    match = _EFFECTIVE_FROM.search(text)
    if match is None:
        return None
    return datetime.strptime(match.group("start"), "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )


def _extract_evidence(db, department: str, version_id: str) -> dict:
    if not EVIDENCE_EXTRACTION_ENABLED or department != "Engineering":
        return {"status": "disabled"}
    try:
        result = {
            "status": "succeeded",
            **extract_and_store_version(db, version_id),
        }
        db.commit()
        return result
    except Exception as extraction_error:
        db.rollback()
        run_id = record_failed_extraction(db, version_id, extraction_error)
        db.commit()
        return {
            "status": "failed",
            "extraction_run_id": run_id,
            "error": str(extraction_error),
        }


def _record_failed_job(db, job_id: str, error: Exception) -> None:
    failed_job = db.get(IngestJob, job_id)
    if failed_job is None:
        return
    failed_job.status = "failed"
    failed_job.completed_at = datetime.now(timezone.utc)
    failed_job.error_message = str(error)[:2000]
    db.commit()
