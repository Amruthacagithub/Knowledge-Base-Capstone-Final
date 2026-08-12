"""Permission-safe document version and temporal comparison API."""
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from backend.config import TEMPORAL_API_ENABLED
from backend.database import SessionLocal
from backend.services.auth import UserContext, authenticate
from backend.services.conflict_detection import detect_version_conflicts, review_conflict
from backend.services.temporal_retrieval import (
    TemporalDocumentUnavailable,
    VersionClaim,
    VersionComparison,
    compare_visible_versions,
    current_visible_version,
    visible_version_effective_at,
    visible_version_history,
)


router = APIRouter(prefix="/api/documents", tags=["document-versions"])
DOCUMENT_NOT_FOUND = "Document not found"


class VersionItem(BaseModel):
    id: str
    version_number: int
    content_hash: str
    file_type: str
    uploaded_at: datetime
    effective_from: datetime | None
    effective_to: datetime | None
    authority_level: int
    is_current: bool


class ClaimItem(BaseModel):
    id: str
    claim_hash: str
    text: str
    predicate: str | None
    object_text: str | None
    polarity: bool
    document_version_id: str


class ConflictItem(BaseModel):
    id: str
    claim_a_id: str
    claim_b_id: str
    conflict_type: str
    status: str
    confidence: float
    rationale: str


class VersionDiffResponse(BaseModel):
    document_id: str
    from_version_id: str
    to_version_id: str
    added: list[ClaimItem]
    removed: list[ClaimItem]
    unchanged: list[ClaimItem]
    conflicts: list[ConflictItem]


class ConflictReviewRequest(BaseModel):
    status: Literal["confirmed", "dismissed"]


@router.get(
    "/{document_id}/versions",
    response_model=list[VersionItem],
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "Temporal API disabled or document unavailable"},
    },
)
def list_document_versions(
    document_id: str,
    authorization: Annotated[str, Header()],
):
    _require_temporal_enabled()
    user_ctx = _require_user(authorization)
    db = SessionLocal()
    try:
        versions = visible_version_history(db, user_ctx, document_id)
        if not versions:
            raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND)
        return [_version_item(version) for version in versions]
    finally:
        db.close()


@router.get(
    "/{document_id}/versions/current",
    response_model=VersionItem,
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "Temporal API disabled or document unavailable"},
    },
)
def get_current_document_version(
    document_id: str,
    authorization: Annotated[str, Header()],
):
    _require_temporal_enabled()
    user_ctx = _require_user(authorization)
    db = SessionLocal()
    try:
        return _version_item(current_visible_version(db, user_ctx, document_id))
    except TemporalDocumentUnavailable as exc:
        raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND) from exc
    finally:
        db.close()


@router.get(
    "/{document_id}/versions/effective",
    response_model=VersionItem,
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "Temporal API disabled or document unavailable"},
    },
)
def get_effective_document_version(
    document_id: str,
    authorization: Annotated[str, Header()],
    at: Annotated[datetime, Query()],
):
    _require_temporal_enabled()
    user_ctx = _require_user(authorization)
    db = SessionLocal()
    try:
        return _version_item(
            visible_version_effective_at(db, user_ctx, document_id, at)
        )
    except TemporalDocumentUnavailable as exc:
        raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND) from exc
    finally:
        db.close()


@router.get(
    "/{document_id}/diff",
    response_model=VersionDiffResponse,
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "Temporal API disabled or document unavailable"},
    },
)
def compare_document_versions(
    document_id: str,
    authorization: Annotated[str, Header()],
    from_version_id: Annotated[str, Query(min_length=1, max_length=100)],
    to_version_id: Annotated[str, Query(min_length=1, max_length=100)],
):
    _require_temporal_enabled()
    user_ctx = _require_user(authorization)
    db = SessionLocal()
    try:
        comparison = compare_visible_versions(
            db,
            user_ctx,
            document_id,
            from_version_id,
            to_version_id,
        )
        conflicts = detect_version_conflicts(
            db,
            document_id,
            from_version_id,
            to_version_id,
        )
        db.commit()
        return _diff_response(comparison, conflicts)
    except TemporalDocumentUnavailable as exc:
        raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND) from exc
    finally:
        db.close()


@router.patch(
    "/{document_id}/conflicts/{conflict_id}",
    response_model=ConflictItem,
    responses={
        401: {"description": "Invalid or expired token"},
        403: {"description": "Admin access required"},
        404: {"description": "Temporal API disabled or conflict unavailable"},
    },
)
def review_document_conflict(
    document_id: str,
    conflict_id: str,
    request: ConflictReviewRequest,
    authorization: Annotated[str, Header()],
):
    _require_temporal_enabled()
    user_ctx = _require_user(authorization)
    if "Admin" not in user_ctx.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    db = SessionLocal()
    try:
        try:
            conflict = review_conflict(
                db,
                document_id,
                conflict_id,
                user_ctx.user_id,
                request.status,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Conflict not found") from exc
        db.commit()
        return _conflict_item(conflict)
    finally:
        db.close()


def _version_item(version) -> VersionItem:
    return VersionItem(
        id=str(version.id),
        version_number=int(version.version_number),
        content_hash=str(version.content_hash),
        file_type=str(version.file_type),
        uploaded_at=version.uploaded_at,
        effective_from=version.effective_from,
        effective_to=version.effective_to,
        authority_level=int(version.authority_level),
        is_current=bool(version.is_current),
    )


def _claim_item(claim: VersionClaim) -> ClaimItem:
    return ClaimItem(
        id=claim.claim_id,
        claim_hash=claim.claim_hash,
        text=claim.claim_text,
        predicate=claim.predicate,
        object_text=claim.object_text,
        polarity=claim.polarity,
        document_version_id=claim.document_version_id,
    )


def _diff_response(comparison: VersionComparison, conflicts) -> VersionDiffResponse:
    return VersionDiffResponse(
        document_id=comparison.document_id,
        from_version_id=comparison.from_version_id,
        to_version_id=comparison.to_version_id,
        added=[_claim_item(claim) for claim in comparison.added],
        removed=[_claim_item(claim) for claim in comparison.removed],
        unchanged=[_claim_item(claim) for claim in comparison.unchanged],
        conflicts=[_conflict_item(conflict) for conflict in conflicts],
    )


def _conflict_item(conflict) -> ConflictItem:
    return ConflictItem(
        id=str(conflict.id),
        claim_a_id=str(conflict.claim_a_id),
        claim_b_id=str(conflict.claim_b_id),
        conflict_type=str(conflict.conflict_type),
        status=str(conflict.status),
        confidence=float(conflict.confidence),
        rationale=str(conflict.rationale),
    )


def _require_temporal_enabled() -> None:
    if not TEMPORAL_API_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")


def _require_user(authorization: str) -> UserContext:
    token = authorization.removeprefix("Bearer ").strip()
    user_ctx = authenticate(token)
    if user_ctx is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_ctx