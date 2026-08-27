from pathlib import Path

import pytest

from backend.services.ingest_service import ingest_document_entry, file_type_from_path


def test_file_type_detection():
    assert file_type_from_path(Path("x.pdf")) == "pdf"
    assert file_type_from_path(Path("x.md")) == "markdown"


@pytest.mark.integration
def test_ingest_single_md(tmp_path):
    """Ingest a temp markdown file without touching production manifest."""
    docs = tmp_path / "documents"
    hr = docs / "hr"
    hr.mkdir(parents=True)
    md = hr / "pytest_doc.md"
    md.write_text("# Pytest Doc\n\nUnique ingest test content zebra.", encoding="utf-8")

    entry = {
        "path": "hr/pytest_doc.md",
        "title": "Pytest Ingest Doc Unique",
        "department": "HR",
        "classification": "public",
    }

    try:
        from backend.services.embedder import ensure_collection
        from backend.services.bm25_index import create_bm25_index

        ensure_collection()
        create_bm25_index()
        result = ingest_document_entry(entry, docs)
        assert result["chunks_indexed"] >= 1
        assert result["file_type"] == "markdown"
    except Exception as e:
        if "Connection" in str(e) or "refused" in str(e).lower():
            pytest.skip("Qdrant not running")
        raise
