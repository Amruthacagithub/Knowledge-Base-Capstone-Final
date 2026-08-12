"""Conservative temporal conflict candidate detection."""
import re
import uuid
from datetime import datetime, timezone

from backend.models import Chunk, ClaimConflict, DocumentVersion, EvidenceClaim


_CONFLICT_NAMESPACE = uuid.UUID("1368161d-afec-4c13-aab0-5ef5ea3b67ac")


def detect_version_conflicts(
    db,
    document_id: str,
    from_version_id: str,
    to_version_id: str,
) -> tuple[ClaimConflict, ...]:
    """Stage differing same-subject/predicate claims for human review."""
    versions = {
        str(version.id): version
        for version in db.query(DocumentVersion)
        .filter(
            DocumentVersion.document_id == document_id,
            DocumentVersion.id.in_([from_version_id, to_version_id]),
        )
        .all()
    }
    if set(versions) != {from_version_id, to_version_id}:
        raise ValueError("both versions must belong to the document")

    first_claims = _claims_by_signature(db, from_version_id)
    second_claims = _claims_by_signature(db, to_version_id)
    candidates = []
    signatures = sorted(set(first_claims) & set(second_claims), key=str)
    for signature in signatures:
        for first_claim in first_claims[signature]:
            for second_claim in second_claims[signature]:
                conflict_type = _conflict_type(first_claim, second_claim)
                if conflict_type is not None:
                    candidates.append(
                        _get_or_create_candidate(
                            db,
                            document_id,
                            first_claim,
                            second_claim,
                            conflict_type,
                        )
                    )
    db.flush()
    return tuple(sorted(candidates, key=lambda conflict: conflict.id))


def review_conflict(
    db,
    document_id: str,
    conflict_id: str,
    reviewer_user_id: str,
    status: str,
) -> ClaimConflict:
    """Apply an explicit human review decision to a conflict candidate."""
    if status not in {"confirmed", "dismissed"}:
        raise ValueError("status must be confirmed or dismissed")
    conflict = (
        db.query(ClaimConflict)
        .filter(
            ClaimConflict.id == conflict_id,
            ClaimConflict.document_id == document_id,
        )
        .one_or_none()
    )
    if conflict is None:
        raise LookupError("Conflict not found")
    conflict.status = status
    conflict.reviewed_by_user_id = reviewer_user_id
    conflict.reviewed_at = datetime.now(timezone.utc)
    db.flush()
    return conflict


def _claims_by_signature(db, document_version_id: str):
    claims = (
        db.query(EvidenceClaim)
        .join(Chunk, Chunk.id == EvidenceClaim.chunk_id)
        .filter(Chunk.document_version_id == document_version_id)
        .order_by(EvidenceClaim.id)
        .all()
    )
    grouped = {}
    for claim in claims:
        if claim.subject_entity_id is None or claim.predicate is None:
            continue
        signature = (
            str(claim.subject_entity_id),
            str(claim.predicate),
        )
        grouped.setdefault(signature, []).append(claim)
    return grouped


def _conflict_type(
    first: EvidenceClaim,
    second: EvidenceClaim,
) -> str | None:
    if bool(first.polarity) != bool(second.polarity):
        return "polarity_change"
    first_object = _normalized_object(first)
    second_object = _normalized_object(second)
    if first_object and second_object and first_object != second_object:
        return "value_change"
    return None


def _normalized_object(claim: EvidenceClaim) -> str:
    value = claim.object_text or _numeric_value(str(claim.claim_text))
    return " ".join(str(value or "").lower().split())


def _numeric_value(text: str) -> str | None:
    number_match = re.search(r"\b\d+(?:\.\d+)?", text)
    if number_match is None:
        return None
    remainder = text[number_match.end() :]
    unit_match = re.match(r"\s*(%|days?|hours?|minutes?)\b", remainder)
    unit = unit_match.group(1) if unit_match else ""
    separator = " " if unit and unit != "%" else ""
    return f"{number_match.group(0)}{separator}{unit}"


def _get_or_create_candidate(
    db,
    document_id: str,
    first_claim: EvidenceClaim,
    second_claim: EvidenceClaim,
    conflict_type: str,
) -> ClaimConflict:
    claim_a_id, claim_b_id = sorted([str(first_claim.id), str(second_claim.id)])
    conflict_id = str(
        uuid.uuid5(
            _CONFLICT_NAMESPACE,
            f"{document_id}:{claim_a_id}:{claim_b_id}:{conflict_type}",
        )
    )
    existing = db.get(ClaimConflict, conflict_id)
    if existing is not None:
        return existing
    rationale = (
        "Same subject and predicate changed polarity across document versions."
        if conflict_type == "polarity_change"
        else (
            "Same subject and predicate have different normalized values "
            "across document versions."
        )
    )
    candidate = ClaimConflict(
        id=conflict_id,
        document_id=document_id,
        claim_a_id=claim_a_id,
        claim_b_id=claim_b_id,
        conflict_type=conflict_type,
        status="candidate",
        confidence=min(float(first_claim.confidence), float(second_claim.confidence)),
        rationale=rationale,
    )
    db.add(candidate)
    return candidate