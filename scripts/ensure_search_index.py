#!/usr/bin/env python3
"""Ensure BM25 search index exists after deploy or cold start."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal
from backend.models import Chunk
from backend.services.bm25_index import bm25_document_count, rebuild_bm25_from_database


def ensure_search_index() -> None:
    db = SessionLocal()
    try:
        chunk_count = db.query(Chunk).count()
        indexed = bm25_document_count()
        print(f"  DB chunks: {chunk_count}; BM25 indexed chunks: {indexed}")

        if chunk_count == 0:
            print("  No chunks in database — running full corpus ingest")
            from scripts.ingest import ingest_all

            ingest_all()
            indexed = bm25_document_count()
            print(f"  BM25 indexed chunks after ingest: {indexed}")
            return

        if indexed == 0:
            print("  Rebuilding BM25 index from database chunks...")
            rebuilt = rebuild_bm25_from_database(db)
            print(f"  Rebuilt BM25 index with {rebuilt} chunks")
            return

        print("  BM25 index already populated")
    finally:
        db.close()


if __name__ == "__main__":
    print("=== Ensure search index ===")
    ensure_search_index()
    print("=== Search index ready ===")
