from backend.routers import documents_router


def test_upload_forbidden_non_admin(client, engineer_headers, tmp_path):
    f = tmp_path / "note.md"
    f.write_text("# Note\n\nTest upload.", encoding="utf-8")
    with open(f, "rb") as fh:
        r = client.post(
            "/api/documents/upload",
            headers=engineer_headers,
            files={"file": ("note.md", fh, "text/markdown")},
            data={
                "title": "Engineer Upload Test",
                "department": "Engineering",
                "classification": "public",
            },
        )
    assert r.status_code == 403


def test_upload_admin(client, admin_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(
        documents_router,
        "ingest_document_entry",
        lambda entry, documents_dir, db, **kwargs: {
            "doc_id": "uploaded-test-document",
            "title": entry["title"],
            "chunks_indexed": 1,
            "file_type": "markdown",
        },
    )
    f = tmp_path / "admin_note.md"
    f.write_text("# Admin Note\n\nUploaded by pytest.", encoding="utf-8")
    with open(f, "rb") as fh:
        r = client.post(
            "/api/documents/upload",
            headers=admin_headers,
            files={"file": ("admin_note.md", fh, "text/markdown")},
            data={
                "title": "Pytest Admin Upload",
                "department": "Engineering",
                "classification": "public",
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data["chunks_indexed"] >= 1
    assert data["doc_id"]


def test_failed_upload_does_not_change_manifest_or_leave_file(
    client,
    admin_headers,
    tmp_path,
    monkeypatch,
):
    manifest_path = documents_router.DOCUMENTS_DIR / "manifest.json"
    manifest_before = manifest_path.read_text(encoding="utf-8")
    uploaded_path = documents_router.DOCUMENTS_DIR / "engineering" / "failed_note.md"
    uploaded_path.unlink(missing_ok=True)

    def fail_ingest(*args, **kwargs):
        raise RuntimeError("synthetic indexing failure")

    monkeypatch.setattr(documents_router, "ingest_document_entry", fail_ingest)
    source = tmp_path / "failed_note.md"
    source.write_text("# Failure fixture", encoding="utf-8")

    with source.open("rb") as upload:
        response = client.post(
            "/api/documents/upload",
            headers=admin_headers,
            files={"file": (source.name, upload, "text/markdown")},
            data={
                "title": "Failed Upload Test",
                "department": "Engineering",
                "classification": "public",
            },
        )

    assert response.status_code == 500
    assert manifest_path.read_text(encoding="utf-8") == manifest_before
    assert not uploaded_path.exists()
