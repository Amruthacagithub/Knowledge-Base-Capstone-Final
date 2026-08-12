import hashlib

import pytest

from backend.models import (
    Chunk,
    Document,
    DocumentVersion,
    Entity,
    EvidenceClaim,
    ExtractionRun,
)
from backend.services.conflict_detection import detect_version_conflicts, review_conflict


def test_conflict_detection_stages_value_change_once(db_session):
    document, first, second = _versions(db_session, "conflict-value")
    subject = _entity(db_session, "pto_policy")
    _claim(db_session, first, "claim-a", subject, "allows", "15 days", "PTO is 15 days.")
    _claim(db_session, second, "claim-b", subject, "allows", "20 days", "PTO is 20 days.")

    first_run = detect_version_conflicts(db_session, document.id, first.id, second.id)
    second_run = detect_version_conflicts(db_session, document.id, first.id, second.id)

    assert len(first_run) == 1
    assert [conflict.id for conflict in second_run] == [first_run[0].id]
    assert first_run[0].status == "candidate"
    assert first_run[0].conflict_type == "value_change"
    assert {first_run[0].claim_a_id, first_run[0].claim_b_id} == {
        "claim-a",
        "claim-b",
    }


def test_conflict_detection_uses_numeric_value_when_object_is_absent(db_session):
    document, first, second = _versions(db_session, "conflict-numeric")
    subject = _entity(db_session, "response_target")
    _claim(db_session, first, "numeric-a", subject, "target", None, "Target is 30 minutes.")
    _claim(db_session, second, "numeric-b", subject, "target", None, "Target is 15 minutes.")

    conflicts = detect_version_conflicts(db_session, document.id, first.id, second.id)

    assert len(conflicts) == 1
    assert conflicts[0].confidence == 0.9


def test_conflict_detection_stages_polarity_change_without_object(db_session):
    document, first, second = _versions(db_session, "conflict-polarity")
    subject = _entity(db_session, "production_deploy")
    _claim(db_session, first, "polarity-a", subject, "allowed", None, "Deploys are allowed.")
    _claim(
        db_session,
        second,
        "polarity-b",
        subject,
        "allowed",
        None,
        "Deploys are not allowed.",
        polarity=False,
    )

    conflicts = detect_version_conflicts(db_session, document.id, first.id, second.id)

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "polarity_change"
    assert "changed polarity" in conflicts[0].rationale


def test_conflict_detection_ignores_unchanged_and_different_predicates(db_session):
    document, first, second = _versions(db_session, "conflict-negative")
    subject = _entity(db_session, "billing")
    _claim(db_session, first, "same-a", subject, "availability", "99.9%", "99.9%")
    _claim(db_session, second, "same-b", subject, "availability", "99.9%", "99.9%")
    _claim(db_session, first, "other-a", subject, "latency", "200 ms", "200 ms")
    _claim(db_session, second, "other-b", subject, "owner", "Platform", "Platform")

    assert detect_version_conflicts(db_session, document.id, first.id, second.id) == ()


def test_conflict_detection_rejects_versions_from_different_documents(db_session):
    first_document, first, _ = _versions(db_session, "conflict-doc-a")
    _second_document, _other_first, other_second = _versions(db_session, "conflict-doc-b")

    with pytest.raises(ValueError, match="both versions must belong to the document"):
        detect_version_conflicts(db_session, first_document.id, first.id, other_second.id)


def test_conflict_review_records_explicit_decision(db_session):
    document, first, second = _versions(db_session, "conflict-review")
    subject = _entity(db_session, "review_policy")
    _claim(db_session, first, "review-a", subject, "value", "old", "Old value.")
    _claim(db_session, second, "review-b", subject, "value", "new", "New value.")
    conflict = detect_version_conflicts(db_session, document.id, first.id, second.id)[0]

    reviewed = review_conflict(
        db_session,
        document.id,
        conflict.id,
        "admin-user",
        "confirmed",
    )

    assert reviewed.status == "confirmed"
    assert reviewed.reviewed_by_user_id == "admin-user"
    assert reviewed.reviewed_at is not None


def _versions(db_session, prefix):
    document = Document(
        id=f"{prefix}-document",
        title=prefix,
        department="HR",
        classification="restricted",
        file_path=f"hr/{prefix}.md",
        source_kind="manifest",
        is_active=True,
    )
    first = _version(document, f"{prefix}-v1", 1, "a")
    second = _version(document, f"{prefix}-v2", 2, "b")
    first.is_current = False
    db_session.add_all([document, first, second])
    db_session.flush()
    return document, first, second


def _version(document, version_id, number, hash_character):
    return DocumentVersion(
        id=version_id,
        document=document,
        version_number=number,
        content_hash=hash_character * 64,
        storage_uri=f"file:///tmp/{version_id}.md",
        file_type="markdown",
        file_size_bytes=10,
        is_current=True,
    )


def _entity(db_session, canonical_name):
    entity = Entity(
        id=f"entity-{canonical_name}",
        entity_type="policy",
        canonical_name=canonical_name,
        display_name=canonical_name.replace("_", " ").title(),
    )
    db_session.add(entity)
    db_session.flush()
    return entity


def _claim(
    db_session,
    version,
    claim_id,
    subject,
    predicate,
    object_text,
    text,
    *,
    polarity=True,
):
    chunk = Chunk(
        id=f"{claim_id}-chunk",
        document_version=version,
        sequence_index=len(version.chunks),
        text_content=text,
        content_hash=hashlib.sha256(f"chunk-{claim_id}".encode()).hexdigest(),
        page_start=1,
        page_end=1,
    )
    run = ExtractionRun(
        id=f"{claim_id}-run",
        document_version_id=version.id,
        extractor_name=claim_id,
        extractor_version="1",
        schema_version="1",
        status="succeeded",
    )
    db_session.add_all([chunk, run])
    db_session.flush()
    db_session.add(
        EvidenceClaim(
            id=claim_id,
            chunk_id=chunk.id,
            extraction_run_id=run.id,
            subject_entity_id=subject.id,
            claim_hash=hashlib.sha256(claim_id.encode()).hexdigest(),
            claim_text=text,
            predicate=predicate,
            object_text=object_text,
            polarity=polarity,
            confidence=0.9,
        )
    )
    db_session.flush()