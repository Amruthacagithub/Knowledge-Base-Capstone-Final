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
from backend.services.evidence_store import extract_and_store_version


def test_evidence_persistence_is_idempotent_and_provenance_complete(db_session):
    version = _version_with_chunk(db_session)

    first = extract_and_store_version(db_session, version.id)
    second = extract_and_store_version(db_session, version.id)

    assert first["extraction_run_id"] == second["extraction_run_id"]
    assert first["mentions"] == second["mentions"] == 4
    assert first["claims"] == second["claims"] == 2
    assert first["relationships"] == second["relationships"] == 2
    assert db_session.query(ExtractionRun).filter_by(document_version_id=version.id).count() == 1
    assert db_session.query(Entity).count() == 3
    assert db_session.query(EntityMention).count() == 4
    assert db_session.query(EvidenceClaim).count() == 2
    assert db_session.query(EvidenceRelationship).count() == 2

    chunk_id = version.chunks[0].id
    assert {
        mention.chunk_id for mention in db_session.query(EntityMention).all()
    } == {chunk_id}
    assert {
        claim.chunk_id for claim in db_session.query(EvidenceClaim).all()
    } == {chunk_id}
    assert {
        relationship.chunk_id
        for relationship in db_session.query(EvidenceRelationship).all()
    } == {chunk_id}


def _version_with_chunk(db_session):
    document = Document(
        id="evidence-store-document",
        title="Evidence Store Document",
        department="Engineering",
        classification="restricted",
        file_path="engineering/evidence-store.md",
        source_kind="manifest",
    )
    version = DocumentVersion(
        id="evidence-store-version",
        document=document,
        version_number=1,
        content_hash="b" * 64,
        storage_uri="file:///tmp/evidence-store.md",
        file_type="markdown",
        file_size_bytes=100,
        is_current=True,
    )
    chunk = Chunk(
        id="evidence-store-version_chunk_0",
        document_version=version,
        sequence_index=0,
        text_content=(
            "Incident INC-5023 affected Billing Service. "
            "Billing Service depends on Stripe Gateway."
        ),
        content_hash="c" * 64,
        page_start=1,
        page_end=1,
    )
    db_session.add_all([document, version, chunk])
    db_session.flush()
    return version