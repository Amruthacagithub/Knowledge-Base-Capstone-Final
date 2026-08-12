from datetime import datetime, timezone

import pytest

from backend.models import (
    Chunk,
    Document,
    DocumentVersion,
    EvidenceClaim,
    ExtractionRun,
)
from backend.services.auth import UserContext
from backend.services.temporal_retrieval import (
    TemporalDocumentUnavailable,
    compare_visible_versions,
    current_visible_version,
    visible_version_effective_at,
    visible_version_history,
)


def test_temporal_selection_returns_current_and_historical_versions(db_session):
    document, first, second = _versioned_document(db_session, "temporal-public", "public")
    user = _user("Employee")

    assert current_visible_version(db_session, user, document.id).id == second.id
    assert visible_version_effective_at(
        db_session,
        user,
        document.id,
        datetime(2025, 6, 1, tzinfo=timezone.utc),
    ).id == first.id
    assert [
        version.id for version in visible_version_history(db_session, user, document.id)
    ] == [first.id, second.id]


def test_temporal_selection_is_permission_safe(db_session):
    document, _first, _second = _versioned_document(
        db_session,
        "temporal-restricted-hr",
        "restricted",
        department="HR",
    )
    engineer = _user("Engineer")
    hr_user = _user("HR")

    assert visible_version_history(db_session, engineer, document.id) == ()
    assert current_visible_version(db_session, hr_user, document.id).version_number == 2
    with pytest.raises(TemporalDocumentUnavailable, match="Document not found"):
        current_visible_version(db_session, engineer, document.id)


def test_version_comparison_reports_added_removed_and_unchanged_claims(db_session):
    document, first, second = _versioned_document(db_session, "temporal-diff", "public")
    _claim(db_session, first, "common", "Employees receive benefits.")
    _claim(db_session, first, "old", "PTO allowance is 15 days.")
    _claim(db_session, second, "common", "Employees receive benefits.")
    _claim(db_session, second, "new", "PTO allowance is 20 days.")

    comparison = compare_visible_versions(
        db_session,
        _user("Employee"),
        document.id,
        first.id,
        second.id,
    )

    assert [claim.claim_hash for claim in comparison.added] == [_hash("new")]
    assert [claim.claim_hash for claim in comparison.removed] == [_hash("old")]
    assert [claim.claim_hash for claim in comparison.unchanged] == [_hash("common")]
    assert comparison.added[0].document_version_id == second.id
    assert comparison.removed[0].document_version_id == first.id


def test_hidden_and_missing_temporal_comparisons_are_indistinguishable(db_session):
    document, first, second = _versioned_document(
        db_session,
        "temporal-hidden",
        "restricted",
        department="HR",
    )
    engineer = _user("Engineer")
    with pytest.raises(TemporalDocumentUnavailable, match="Document not found"):
        compare_visible_versions(db_session, engineer, document.id, first.id, second.id)
    with pytest.raises(TemporalDocumentUnavailable, match="Document not found"):
        compare_visible_versions(db_session, engineer, "missing", "v1", "v2")


def _versioned_document(db_session, prefix, classification, department="Engineering"):
    document = Document(
        id=f"{prefix}-document",
        title=prefix,
        department=department,
        classification=classification,
        file_path=f"{department.lower()}/{prefix}.md",
        source_kind="manifest",
        is_active=True,
    )
    first = DocumentVersion(
        id=f"{prefix}-v1",
        document=document,
        version_number=1,
        content_hash="a" * 64,
        storage_uri=f"file:///tmp/{prefix}-v1.md",
        file_type="markdown",
        file_size_bytes=10,
        effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
        effective_to=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_current=False,
    )
    second = DocumentVersion(
        id=f"{prefix}-v2",
        document=document,
        version_number=2,
        content_hash="b" * 64,
        storage_uri=f"file:///tmp/{prefix}-v2.md",
        file_type="markdown",
        file_size_bytes=10,
        effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_current=True,
    )
    db_session.add_all([document, first, second])
    db_session.flush()
    return document, first, second


def _claim(db_session, version, label, text):
    chunk = Chunk(
        id=f"{version.id}-{label}-chunk",
        document_version=version,
        sequence_index=len(version.chunks),
        text_content=text,
        content_hash=_hash(f"chunk-{label}"),
        page_start=1,
        page_end=1,
    )
    run = ExtractionRun(
        id=f"{version.id}-{label}-run",
        document_version_id=version.id,
        extractor_name=f"test-{label}",
        extractor_version="1",
        schema_version="1",
        status="succeeded",
    )
    db_session.add_all([chunk, run])
    db_session.flush()
    claim = EvidenceClaim(
        id=f"{version.id}-{label}-claim",
        chunk_id=chunk.id,
        extraction_run_id=run.id,
        claim_hash=_hash(label),
        claim_text=text,
        predicate="states",
        polarity=True,
        confidence=1.0,
    )
    db_session.add(claim)
    db_session.flush()


def _hash(value):
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _user(role):
    return UserContext(
        user_id=f"temporal-{role}",
        email=f"{role.lower()}@example.com",
        department="Engineering",
        roles=[role],
    )