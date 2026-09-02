"""
Ingestion script — parse, chunk, embed, and index all documents.
Run: python scripts/ingest.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import DOCUMENTS_DIR, VECTOR_SEARCH_ENABLED
from backend.services.bm25_index import create_bm25_index
from backend.services.document_lifecycle import (
    active_upload_entries,
    deactivate_missing_manifest_documents,
)
from backend.services.ingest_service import canonicalize_manifest_entry, ingest_document_entry
from backend.services.document_storage import get_document_storage
from backend.models import Document
from backend.database import SessionLocal

if VECTOR_SEARCH_ENABLED:
    from backend.services.embedder import ensure_collection, prune_points_for_missing_documents


def load_manifest() -> list[dict]:
    manifest_path = DOCUMENTS_DIR / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found at {manifest_path}")
        sys.exit(1)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def ingest_all():
    print("=== EKIP Document Ingestion ===\n")

    manifest = load_manifest()
    print(f"Found {len(manifest)} documents in manifest.\n")

    if VECTOR_SEARCH_ENABLED:
        ensure_collection()
    create_bm25_index()

    db = SessionLocal()
    total_chunks = 0
    success_count = 0
    active_doc_ids: set[str] = set()
    active_manifest_doc_ids: set[str] = set()
    entries: list[dict] = []
    storage = get_document_storage()

    try:
        upload_entries = active_upload_entries(db)
        entries = [
            {**canonicalize_manifest_entry(entry), "source_kind": "manifest"}
            for entry in manifest
        ] + upload_entries

        for entry in entries:
            print(f"  [{entry['department']}] {entry['title']}")
            try:
                source_file_path = (
                    storage.resolve_local_path(entry["path"])
                    if entry["source_kind"] == "upload"
                    else None
                )
                result = ingest_document_entry(
                    entry,
                    DOCUMENTS_DIR,
                    db=db,
                    source_file_path=source_file_path,
                )
                label = "BM25" if not VECTOR_SEARCH_ENABLED else "Qdrant + BM25"
                print(
                    f"    → {result['chunks_indexed']} chunks "
                    f"({result['file_type']}) → {label}"
                )
                total_chunks += result["chunks_indexed"]
                success_count += 1
                active_doc_ids.add(result["doc_id"])
                if entry["source_kind"] == "manifest":
                    active_manifest_doc_ids.add(result["doc_id"])
            except FileNotFoundError as e:
                print(f"    ⚠ {e}, skipping.")
            except Exception as e:
                print(f"    ⚠ Error: {e}, skipping.")
            print()

        stale_points_removed = 0
        if VECTOR_SEARCH_ENABLED and success_count == len(entries):
            deactivate_missing_manifest_documents(db, active_manifest_doc_ids)
            db.commit()
            active_doc_ids = {
                str(document_id)
                for (document_id,) in db.query(Document.id)
                .filter(Document.is_active.is_(True))
                .all()
            }
            stale_points_removed = prune_points_for_missing_documents(active_doc_ids)
        elif success_count == len(entries):
            deactivate_missing_manifest_documents(db, active_manifest_doc_ids)
            db.commit()
    finally:
        db.close()

    print(
        f"=== Done! Ingested {success_count}/{len(entries)} documents, "
        f"{total_chunks} chunks total, "
        f"removed {stale_points_removed} stale vectors. ==="
    )


if __name__ == "__main__":
    ingest_all()
