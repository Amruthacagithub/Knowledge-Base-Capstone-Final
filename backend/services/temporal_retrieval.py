"""Authorization-safe temporal document selection and version comparison."""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_

from backend.models import Chunk, Document, DocumentVersion, EvidenceClaim
from backend.services.auth import UserContext
from backend.services.evidence_access import apply_document_access


DOCUMENT_NOT_FOUND = "Document not found"


class TemporalDocumentUnavailable(LookupError):
    """Raised for missing, hidden, inactive, or unavailable document versions."""


@dataclass(frozen=True)
class VersionClaim:
    claim_id: str
    claim_hash: str
    claim_text: str
    predicate: str | None
    object_text: str | None
    polarity: bool
    document_version_id: str


@dataclass(frozen=True)
class VersionComparison:
    document_id: str
    from_version_id: str
    to_version_id: str
    added: tuple[VersionClaim, ...]
    removed: tuple[VersionClaim, ...]
    unchanged: tuple[VersionClaim, ...]


def visible_version_history(
    db,
    user_ctx: UserContext,
    document_id: str,
) -> tuple[DocumentVersion, ...]:
    """Return all versions of an active document visible to the user."""
    query = _visible_version_query(db, user_ctx, document_id)
    return tuple(query.order_by(DocumentVersion.version_number).all())


def current_visible_version(
    db,
    user_ctx: UserContext,
    document_id: str,
) -> DocumentVersion:
    """Return the authoritative current visible version."""
    version = (
        _visible_version_query(db, user_ctx, document_id)
        .filter(DocumentVersion.is_current.is_(True))
        .order_by(
            DocumentVersion.authority_level.desc(),
            DocumentVersion.version_number.desc(),
        )
        .first()
    )
    if version is None:
        raise TemporalDocumentUnavailable(DOCUMENT_NOT_FOUND)
    return version


def visible_version_effective_at(
    db,
    user_ctx: UserContext,
    document_id: str,
    effective_at: datetime,
) -> DocumentVersion:
    """Return the highest-authority visible version effective at a timestamp."""
    version = (
        _visible_version_query(db, user_ctx, document_id)
        .filter(
            or_(
                DocumentVersion.effective_from.is_(None),
                DocumentVersion.effective_from <= effective_at,
            ),
            or_(
                DocumentVersion.effective_to.is_(None),
                DocumentVersion.effective_to > effective_at,
            ),
        )
        .order_by(
            DocumentVersion.authority_level.desc(),
            DocumentVersion.version_number.desc(),
        )
        .first()
    )
    if version is None:
        raise TemporalDocumentUnavailable(DOCUMENT_NOT_FOUND)
    return version


def compare_visible_versions(
    db,
    user_ctx: UserContext,
    document_id: str,
    from_version_id: str,
    to_version_id: str,
) -> VersionComparison:
    """Compare exact extracted claim sets from two visible versions."""
    visible_versions = {
        str(version.id): version
        for version in _visible_version_query(db, user_ctx, document_id)
        .filter(DocumentVersion.id.in_([from_version_id, to_version_id]))
        .all()
    }
    if set(visible_versions) != {from_version_id, to_version_id}:
        raise TemporalDocumentUnavailable(DOCUMENT_NOT_FOUND)

    from_claims = _claims_by_hash(db, from_version_id)
    to_claims = _claims_by_hash(db, to_version_id)
    return VersionComparison(
        document_id=document_id,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
        added=_ordered_claims(to_claims, set(to_claims) - set(from_claims)),
        removed=_ordered_claims(from_claims, set(from_claims) - set(to_claims)),
        unchanged=_ordered_claims(to_claims, set(from_claims) & set(to_claims)),
    )


def _visible_version_query(db, user_ctx: UserContext, document_id: str):
    query = (
        db.query(DocumentVersion)
        .join(Document, Document.id == DocumentVersion.document_id)
        .filter(Document.id == document_id, Document.is_active.is_(True))
    )
    return apply_document_access(query, user_ctx)


def _claims_by_hash(db, document_version_id: str) -> dict[str, VersionClaim]:
    rows = (
        db.query(EvidenceClaim)
        .join(Chunk, Chunk.id == EvidenceClaim.chunk_id)
        .filter(Chunk.document_version_id == document_version_id)
        .order_by(EvidenceClaim.id)
        .all()
    )
    return {
        str(claim.claim_hash): VersionClaim(
            claim_id=str(claim.id),
            claim_hash=str(claim.claim_hash),
            claim_text=str(claim.claim_text),
            predicate=str(claim.predicate) if claim.predicate is not None else None,
            object_text=str(claim.object_text) if claim.object_text is not None else None,
            polarity=bool(claim.polarity),
            document_version_id=document_version_id,
        )
        for claim in rows
    }


def _ordered_claims(
    claims_by_hash: dict[str, VersionClaim],
    hashes: set[str],
) -> tuple[VersionClaim, ...]:
    return tuple(claims_by_hash[claim_hash] for claim_hash in sorted(hashes))