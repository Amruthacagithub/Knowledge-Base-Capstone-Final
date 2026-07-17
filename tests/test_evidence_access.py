from backend.models import (
    Chunk,
    Document,
    DocumentVersion,
    Entity,
    EntityMention,
    EvidenceClaim,
    EvidenceRelationship,
    ExtractionRun,
)
from backend.services.auth import UserContext
from backend.services.evidence_access import (
    visible_claims,
    visible_entities,
    visible_relationships,
)


def test_evidence_queries_do_not_leak_restricted_graph_artifacts(db_session):
    _evidence(db_session, "public-eng", "Engineering", "public")
    _evidence(db_session, "restricted-hr", "HR", "restricted")

    engineer = _user("Engineer")
    admin = _user("Admin")

    assert _ids(visible_entities(db_session, engineer)) == {"public-eng-entity-a", "public-eng-entity-b"}
    assert _ids(visible_claims(db_session, engineer)) == {"public-eng-claim"}
    assert _ids(visible_relationships(db_session, engineer)) == {"public-eng-relationship"}

    assert _ids(visible_entities(db_session, admin)) == {
        "public-eng-entity-a",
        "public-eng-entity-b",
        "restricted-hr-entity-a",
        "restricted-hr-entity-b",
    }
    assert _ids(visible_claims(db_session, admin)) == {
        "public-eng-claim",
        "restricted-hr-claim",
    }


def test_department_role_sees_own_restricted_evidence(db_session):
    _evidence(db_session, "restricted-hr-own", "HR", "restricted")

    hr_user = _user("HR")
    employee = _user("Employee")

    assert _ids(visible_claims(db_session, hr_user)) == {"restricted-hr-own-claim"}
    assert visible_claims(db_session, employee) == []
    assert visible_entities(db_session, employee) == []
    assert visible_relationships(db_session, employee) == []


def _evidence(db_session, prefix, department, classification):
    document = Document(
        id=f"{prefix}-document",
        title=prefix,
        department=department,
        classification=classification,
        file_path=f"{department.lower()}/{prefix}.md",
        source_kind="manifest",
        is_active=True,
    )
    version = DocumentVersion(
        id=f"{prefix}-version",
        document=document,
        version_number=1,
        content_hash=("d" if classification == "public" else "e") * 64,
        storage_uri=f"file:///tmp/{prefix}.md",
        file_type="markdown",
        file_size_bytes=20,
        is_current=True,
    )
    chunk = Chunk(
        id=f"{prefix}-chunk",
        document_version=version,
        sequence_index=0,
        text_content="Entity A depends on Entity B.",
        content_hash="f" * 64,
        page_start=1,
        page_end=1,
    )
    run = ExtractionRun(
        id=f"{prefix}-run",
        document_version_id=version.id,
        extractor_name="test",
        extractor_version="1",
        schema_version="1",
        status="succeeded",
    )
    entity_a = Entity(
        id=f"{prefix}-entity-a",
        entity_type="system",
        canonical_name=f"{prefix}_a",
        display_name="Entity A",
    )
    entity_b = Entity(
        id=f"{prefix}-entity-b",
        entity_type="system",
        canonical_name=f"{prefix}_b",
        display_name="Entity B",
    )
    mention = EntityMention(
        id=f"{prefix}-mention",
        entity_id=entity_a.id,
        chunk_id=chunk.id,
        extraction_run_id=run.id,
        surface_text="Entity A",
        start_char=0,
        end_char=8,
        confidence=1.0,
    )
    second_mention = EntityMention(
        id=f"{prefix}-mention-b",
        entity_id=entity_b.id,
        chunk_id=chunk.id,
        extraction_run_id=run.id,
        surface_text="Entity B",
        start_char=20,
        end_char=28,
        confidence=1.0,
    )
    claim = EvidenceClaim(
        id=f"{prefix}-claim",
        chunk_id=chunk.id,
        extraction_run_id=run.id,
        subject_entity_id=entity_a.id,
        claim_hash=("1" if classification == "public" else "2") * 64,
        claim_text="Entity A depends on Entity B.",
        predicate="depends_on",
        object_text="Entity B",
        polarity=True,
        confidence=1.0,
    )
    relationship = EvidenceRelationship(
        id=f"{prefix}-relationship",
        chunk_id=chunk.id,
        extraction_run_id=run.id,
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relationship_type="depends_on",
        evidence_text=claim.claim_text,
        confidence=1.0,
    )
    db_session.add_all(
        [
            document,
            version,
            chunk,
            run,
            entity_a,
            entity_b,
            mention,
            second_mention,
            claim,
            relationship,
        ]
    )
    db_session.flush()


def _user(role):
    return UserContext(
        user_id=f"test-{role}",
        email=f"{role.lower()}@example.com",
        department="Engineering",
        roles=["Employee", role],
    )


def _ids(items):
    return {item.id for item in items}