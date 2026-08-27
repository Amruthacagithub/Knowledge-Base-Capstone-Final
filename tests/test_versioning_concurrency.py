from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest

from backend.database import SessionLocal
from backend.models import Document, DocumentVersion
from backend.services.versioning import ensure_document_version


@pytest.mark.integration
def test_concurrent_versions_are_serialized(tmp_path):
    document_id = f"concurrent-{uuid4()}"
    first_source = _source(tmp_path, "first.md", "Rotate every 12 months.")
    second_source = _source(tmp_path, "second.md", "Rotate every 90 days.")
    db = SessionLocal()
    try:
        db.add(
            Document(
                id=document_id,
                title=document_id,
                department="Engineering",
                classification="public",
                file_path="engineering/concurrent.md",
            )
        )
        db.commit()
    finally:
        db.close()

    barrier = Barrier(2)

    def create_version(source: Path) -> int:
        session = SessionLocal()
        try:
            document = session.get(Document, document_id)
            barrier.wait(timeout=10)
            version, _ = ensure_document_version(
                session,
                document=document,
                file_path=source,
                file_type="markdown",
                chunks=[{"text": source.read_text(encoding="utf-8")}],
            )
            session.commit()
            return version.version_number
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(create_version, first_source),
                executor.submit(create_version, second_source),
            ]
            assert sorted(future.result(timeout=20) for future in futures) == [1, 2]

        verify = SessionLocal()
        try:
            versions = (
                verify.query(DocumentVersion)
                .filter_by(document_id=document_id)
                .order_by(DocumentVersion.version_number)
                .all()
            )
            assert [version.version_number for version in versions] == [1, 2]
            assert sum(version.is_current for version in versions) == 1
            assert versions[0].superseded_by_id == versions[1].id
        finally:
            verify.close()
    finally:
        cleanup = SessionLocal()
        try:
            document = cleanup.get(Document, document_id)
            if document is not None:
                cleanup.delete(document)
                cleanup.commit()
        finally:
            cleanup.close()


def _source(tmp_path: Path, name: str, content: str) -> Path:
    source = tmp_path / name
    source.write_text(content, encoding="utf-8")
    return source