"""Immutable document-version and relational chunk lifecycle."""
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func

from backend.models import Chunk, Document, DocumentVersion
from backend.services.chunk_identity import build_chunk_id


_DOCUMENT_VERSION_NAMESPACE = uuid.UUID("af7cf925-0d1d-469e-a4e1-67b3766f99f8")


def hash_file(file_path: Path) -> str:
    """Return the SHA-256 digest of a source file."""
    digest = hashlib.sha256()
    with file_path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_text(text: str) -> str:
    """Return the SHA-256 digest of normalized stored chunk text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_document_version_id(document_id: str, content_hash: str) -> str:
    """Build a deterministic identity for one document and content digest."""
    if not document_id or len(content_hash) != 64:
        raise ValueError("document_id and a SHA-256 content hash are required")
    return str(uuid.uuid5(_DOCUMENT_VERSION_NAMESPACE, f"{document_id}:{content_hash}"))


def ensure_document_version(
    db,
    *,
    document: Document,
    file_path: Path,
    file_type: str,
    chunks: list[dict],
    uploaded_by_user_id: str | None = None,
    effective_from: datetime | None = None,
    authority_level: int = 50,
    storage_uri: str | None = None,
) -> tuple[DocumentVersion, bool]:
    """Get an identical version or stage a new immutable version and chunks."""
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    if not chunks:
        raise ValueError("at least one chunk is required")
    if not 0 <= authority_level <= 100:
        raise ValueError("authority_level must be between 0 and 100")

    locked_document = (
        db.query(Document)
        .filter(Document.id == document.id)
        .with_for_update()
        .one()
    )

    content_hash = hash_file(file_path)
    existing = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.document_id == locked_document.id,
            DocumentVersion.content_hash == content_hash,
        )
        .first()
    )
    if existing is not None:
        if not existing.is_current:
            current_versions = (
                db.query(DocumentVersion)
                .filter(
                    DocumentVersion.document_id == locked_document.id,
                    DocumentVersion.is_current.is_(True),
                )
                .all()
            )
            for current_version in current_versions:
                current_version.is_current = False
                current_version.effective_to = current_version.effective_to or datetime.now(
                    timezone.utc
                )
            existing.is_current = True
            existing.effective_to = None
            existing.superseded_by_id = None
        return existing, False

    current = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.document_id == locked_document.id,
            DocumentVersion.is_current.is_(True),
        )
        .order_by(DocumentVersion.version_number.desc())
        .first()
    )
    max_version = (
        db.query(func.max(DocumentVersion.version_number))
        .filter(DocumentVersion.document_id == locked_document.id)
        .scalar()
        or 0
    )
    valid_from = effective_from or datetime.now(timezone.utc)
    version = DocumentVersion(
        id=build_document_version_id(str(locked_document.id), content_hash),
        document_id=locked_document.id,
        version_number=max_version + 1,
        content_hash=content_hash,
        storage_uri=storage_uri or file_path.resolve().as_uri(),
        file_type=file_type,
        file_size_bytes=file_path.stat().st_size,
        uploaded_by_user_id=uploaded_by_user_id,
        effective_from=valid_from,
        authority_level=authority_level,
        is_current=True,
    )
    db.add(version)
    db.flush()

    if current is not None:
        current.is_current = False
        current.effective_to = valid_from
        current.superseded_by_id = version.id

    for sequence_index, chunk_data in enumerate(chunks):
        text = str(chunk_data["text"])
        db.add(
            Chunk(
                id=build_chunk_id(version.id, sequence_index),
                document_version_id=version.id,
                sequence_index=sequence_index,
                text_content=text,
                content_hash=hash_text(text),
                page_start=int(chunk_data.get("page_start", 1)),
                page_end=int(chunk_data.get("page_end", 1)),
                section_path=chunk_data.get("section_path"),
            )
        )
    db.flush()
    return version, True