"""
Documents router — list, read, download, and upload documents.
"""
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Header, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.config import DOCUMENTS_DIR
from backend.database import SessionLocal
from backend.models import Document
from backend.services.auth import UserContext, authenticate
from backend.services.document_access import user_can_access_document
from backend.services.document_storage import get_document_storage
from backend.services.parser import parse_document
from backend.services.ingest_service import ingest_document_entry, file_type_from_path

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}
INGESTION_FAILED = "Document ingestion failed"
AUTH_RESPONSES = {401: {"description": "Invalid or expired token"}}
DOCUMENT_RESPONSES = {
    **AUTH_RESPONSES,
    403: {"description": "Document access denied"},
    404: {"description": "Document or source file not found"},
}
UPLOAD_RESPONSES = {
    **AUTH_RESPONSES,
    400: {"description": "Invalid upload metadata, type, or size"},
    403: {"description": "Admin access required"},
    500: {"description": INGESTION_FAILED},
}


class DocumentSummary(BaseModel):
    id: str
    title: str
    department: str
    classification: str
    file_path: str
    file_type: str = "markdown"


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]
    total: int


class PageSegment(BaseModel):
    page: int
    text: str


class DocumentContentResponse(BaseModel):
    id: str
    title: str
    department: str
    classification: str
    content: str
    file_type: str = "markdown"
    pages: list[PageSegment] = Field(default_factory=list)
    highlight_excerpt: str | None = None
    highlight_excerpts: list[str] = Field(default_factory=list)
    highlight_page: int | None = None


class UploadResponse(BaseModel):
    doc_id: str
    title: str
    chunks_indexed: int
    file_type: str


def _require_user(authorization: str) -> UserContext:
    token = authorization.replace("Bearer ", "")
    user_ctx = authenticate(token)
    if not user_ctx:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_ctx


def _require_admin(user_ctx: UserContext) -> None:
    if "Admin" not in user_ctx.roles:
        raise HTTPException(status_code=403, detail="Admin access required")


def _load_doc_content(doc: Document):
    file_path = get_document_storage().resolve_local_path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file missing on disk")
    segments = parse_document(file_path)
    file_type = file_type_from_path(file_path)
    pages = [PageSegment(page=int(s.get("page", 1)), text=s["text"]) for s in segments]
    content = "\n\n".join(seg["text"] for seg in segments)
    return file_path, file_type, pages, content


def _dedupe_excerpts(highlight: list[str] | None) -> list[str]:
    excerpts = []
    if highlight:
        for h in highlight:
            if h and h.strip():
                excerpts.append(h.strip()[:2000])
    seen = set()
    unique = []
    for e in excerpts:
        key = e[:80]
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def _get_active_document(db, doc_id: str, user_ctx: UserContext) -> Document:
    document = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.is_active.is_(True))
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not user_can_access_document(document, user_ctx):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this document",
        )
    return document


def _scope_excerpts_to_page(
    excerpts: list[str],
    pages: list[PageSegment],
    page: int | None,
    file_type: str,
) -> list[str]:
    if page is None or file_type != "pdf" or not excerpts:
        return excerpts
    page_text = next((segment.text for segment in pages if segment.page == page), None)
    if not page_text:
        return excerpts
    matching = [
        excerpt
        for excerpt in excerpts
        if excerpt in page_text or excerpt[:80] in page_text
    ]
    return matching or excerpts


@router.get("", response_model=DocumentListResponse, responses=AUTH_RESPONSES)
def list_documents(authorization: Annotated[str, Header()]):
    user_ctx = _require_user(authorization)
    db = SessionLocal()
    try:
        all_docs = (
            db.query(Document)
            .filter(Document.is_active.is_(True))
            .order_by(Document.department, Document.title)
            .all()
        )
        visible = [
            DocumentSummary(
                id=d.id,
                title=d.title,
                department=d.department,
                classification=d.classification,
                file_path=d.file_path,
                file_type=file_type_from_path(DOCUMENTS_DIR / d.file_path),
            )
            for d in all_docs
            if user_can_access_document(d, user_ctx)
        ]
        return DocumentListResponse(documents=visible, total=len(visible))
    finally:
        db.close()


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses=UPLOAD_RESPONSES,
)
async def upload_document(
    authorization: Annotated[str, Header()],
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    department: Annotated[str, Form()],
    classification: Annotated[str, Form()],
):
    """Admin-only: upload and index a new document."""
    user_ctx = _require_user(authorization)
    _require_admin(user_ctx)

    if classification not in ("public", "restricted"):
        raise HTTPException(status_code=400, detail="classification must be public or restricted")
    if department not in ("HR", "Engineering", "Sales"):
        raise HTTPException(status_code=400, detail="Invalid department")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Allowed types: .pdf, .md, .txt")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    storage = get_document_storage()
    stored = storage.save_upload(department, file.filename or "upload", data)
    entry = {
        "path": stored.relative_path,
        "title": title.strip(),
        "department": department,
        "classification": classification,
        "source_id": None,
        "source_kind": "upload",
        "storage_uri": stored.storage_uri,
    }

    db = SessionLocal()
    try:
        result = ingest_document_entry(
            entry,
            DOCUMENTS_DIR,
            db=db,
            triggered_by_user_id=user_ctx.user_id,
            source_file_path=stored.local_path,
        )
    except Exception as exc:
        storage.delete(stored.relative_path)
        logger.exception(INGESTION_FAILED, exc_info=exc)
        raise HTTPException(status_code=500, detail=INGESTION_FAILED) from exc
    finally:
        db.close()

    return UploadResponse(
        doc_id=result["doc_id"],
        title=result["title"],
        chunks_indexed=result["chunks_indexed"],
        file_type=result["file_type"],
    )

@router.get("/{doc_id}/file", responses=DOCUMENT_RESPONSES)
def download_document_file(
    doc_id: str,
    authorization: Annotated[str, Header()],
):
    """Stream the raw document file (PDF or text source)."""
    user_ctx = _require_user(authorization)
    db = SessionLocal()
    try:
        doc = _get_active_document(db, doc_id, user_ctx)
        file_path, file_type, _, _ = _load_doc_content(doc)
        media = "application/pdf" if file_type == "pdf" else "text/plain"
        return FileResponse(path=file_path, media_type=media, filename=file_path.name)
    finally:
        db.close()


@router.get(
    "/{doc_id}",
    response_model=DocumentContentResponse,
    responses=DOCUMENT_RESPONSES,
)
def get_document(
    doc_id: str,
    authorization: Annotated[str, Header()],
    highlight: Annotated[list[str] | None, Query()] = None,
    page: Annotated[
        int | None,
        Query(description="Scope highlights to this PDF page"),
    ] = None,
):
    user_ctx = _require_user(authorization)
    db = SessionLocal()
    try:
        doc = _get_active_document(db, doc_id, user_ctx)
        _, file_type, pages, content = _load_doc_content(doc)
        excerpts = _dedupe_excerpts(highlight)
        excerpts = _scope_excerpts_to_page(excerpts, pages, page, file_type)

        return DocumentContentResponse(
            id=doc.id,
            title=doc.title,
            department=doc.department,
            classification=doc.classification,
            content=content,
            file_type=file_type,
            pages=pages if file_type == "pdf" else [],
            highlight_excerpt=excerpts[0] if len(excerpts) == 1 else None,
            highlight_excerpts=excerpts,
            highlight_page=page,
        )
    finally:
        db.close()
