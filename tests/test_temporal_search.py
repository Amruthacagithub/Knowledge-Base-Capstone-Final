import hashlib
from datetime import datetime, timezone

from backend.models import Chunk, Document, DocumentVersion
from backend.services.auth import UserContext
from backend.services.temporal_search import retrieve_temporal_candidates


def test_current_query_returns_only_current_authoritative_version(db_session):
    document, first, second = _versioned_document(db_session, "leave-current", "public")

    results = retrieve_temporal_candidates(
        db_session,
        _user("Employee"),
        "What is the current leave allowance?",
    )

    assert {result["document_version_id"] for result in results} == {second.id}
    assert all(result["version_number"] == 2 for result in results)
    assert first.id not in {result["document_version_id"] for result in results}


def test_as_of_query_selects_effective_historical_version(db_session):
    _document, first, _second = _versioned_document(
        db_session,
        "leave-history",
        "public",
    )

    results = retrieve_temporal_candidates(
        db_session,
        _user("Employee"),
        "What was the leave allowance as of June 2025?",
    )

    assert {result["document_version_id"] for result in results} == {first.id}


def test_change_query_returns_evidence_from_both_versions(db_session):
    _document, first, second = _versioned_document(
        db_session,
        "leave-change",
        "public",
    )

    results = retrieve_temporal_candidates(
        db_session,
        _user("Employee"),
        "What changed in the leave allowance?",
    )

    assert {result["document_version_id"] for result in results} == {
        first.id,
        second.id,
    }


def test_restricted_history_is_not_visible_cross_department(db_session):
    _versioned_document(
        db_session,
        "compensation-history",
        "restricted",
        department="HR",
    )

    hidden = retrieve_temporal_candidates(
        db_session,
        _user("Engineer"),
        "What is the current compensation allowance?",
    )
    visible = retrieve_temporal_candidates(
        db_session,
        _user("HR"),
        "What is the current compensation allowance?",
    )

    assert hidden == []
    assert visible


def _versioned_document(db_session, prefix, classification, department="Engineering"):
    document = Document(
        id=f"{prefix}-document",
        title=prefix.replace("-", " "),
        department=department,
        classification=classification,
        file_path=f"{department.lower()}/{prefix}.md",
        source_kind="manifest",
        is_active=True,
    )
    first = _version(document, prefix, 1, "a", False, 50)
    second = _version(document, prefix, 2, "b", True, 80)
    db_session.add_all([document, first, second])
    db_session.flush()
    _chunk(db_session, first, f"The {prefix} allowance was 15 days.")
    _chunk(db_session, second, f"The {prefix} allowance is 20 days.")
    return document, first, second


def _version(document, prefix, number, hash_character, current, authority):
    boundary = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return DocumentVersion(
        id=f"{prefix}-v{number}",
        document=document,
        version_number=number,
        content_hash=hash_character * 64,
        storage_uri=f"file:///tmp/{prefix}-v{number}.md",
        file_type="markdown",
        file_size_bytes=10,
        effective_from=(
            datetime(2025, 1, 1, tzinfo=timezone.utc) if number == 1 else boundary
        ),
        effective_to=boundary if number == 1 else None,
        authority_level=authority,
        is_current=current,
    )


def _chunk(db_session, version, text):
    chunk_id = f"{version.id}-chunk"
    db_session.add(
        Chunk(
            id=chunk_id,
            document_version=version,
            sequence_index=0,
            text_content=text,
            content_hash=hashlib.sha256(chunk_id.encode()).hexdigest(),
            page_start=1,
            page_end=1,
        )
    )
    db_session.flush()


def _user(role):
    return UserContext(
        user_id=f"temporal-search-{role}",
        email=f"{role.lower()}@example.com",
        department="Engineering",
        roles=[role],
    )