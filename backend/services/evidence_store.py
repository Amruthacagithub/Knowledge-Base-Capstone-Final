"""Persistence for deterministic evidence extraction artifacts."""
from datetime import datetime, timezone

from backend.models import (
    Chunk,
    Entity,
    EntityMention,
    EvidenceClaim,
    EvidenceRelationship,
    ExtractionRun,
)
from backend.services.evidence_extractor import (
    EXTRACTOR_NAME,
    EXTRACTOR_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    extract_chunk_evidence,
    extraction_run_id,
)


def extract_and_store_version(db, document_version_id: str) -> dict:
    """Replace this extractor version's evidence for one document version."""
    run_id = extraction_run_id(document_version_id)
    _clear_previous_runs(db, document_version_id)

    run = ExtractionRun(
        id=run_id,
        document_version_id=document_version_id,
        extractor_name=EXTRACTOR_NAME,
        extractor_version=EXTRACTOR_VERSION,
        schema_version=EVIDENCE_SCHEMA_VERSION,
        status="running",
    )
    db.add(run)
    db.flush()

    counts = {"entities": 0, "mentions": 0, "claims": 0, "relationships": 0}
    try:
        chunks = (
            db.query(Chunk)
            .filter(Chunk.document_version_id == document_version_id)
            .order_by(Chunk.sequence_index)
            .all()
        )
        for chunk in chunks:
            evidence = extract_chunk_evidence(str(chunk.id), str(chunk.text_content))
            _store_chunk_evidence(db, run.id, chunk.id, evidence, counts)

        run.status = "succeeded"
        run.completed_at = datetime.now(timezone.utc)
        db.flush()
        return {"extraction_run_id": run.id, **counts}
    except Exception as exc:
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = str(exc)[:2000]
        db.flush()
        raise


def record_failed_extraction(db, document_version_id: str, error: Exception) -> str:
    """Persist a failed first-time extraction attempt without replacing success."""
    run_id = extraction_run_id(document_version_id)
    run = db.get(ExtractionRun, run_id)
    if run is not None and run.status == "succeeded":
        return run.id
    if run is None:
        run = ExtractionRun(
            id=run_id,
            document_version_id=document_version_id,
            extractor_name=EXTRACTOR_NAME,
            extractor_version=EXTRACTOR_VERSION,
            schema_version=EVIDENCE_SCHEMA_VERSION,
            status="failed",
        )
        db.add(run)
    run.status = "failed"
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = str(error)[:2000]
    db.flush()
    return run.id


def _clear_previous_runs(db, document_version_id: str) -> None:
    runs = (
        db.query(ExtractionRun)
        .filter(
            ExtractionRun.document_version_id == document_version_id,
            ExtractionRun.extractor_name == EXTRACTOR_NAME,
        )
        .all()
    )
    if not runs:
        return
    run_ids = [run.id for run in runs]
    for model in (EvidenceRelationship, EvidenceClaim, EntityMention):
        (
            db.query(model)
            .filter(model.extraction_run_id.in_(run_ids))
            .delete(synchronize_session=False)
        )
    for run in runs:
        db.delete(run)
    db.flush()


def _store_chunk_evidence(db, run_id, chunk_id, evidence, counts) -> None:
    for extracted_entity in evidence.entities:
        if db.get(Entity, extracted_entity.id) is not None:
            continue
        db.add(
            Entity(
                id=extracted_entity.id,
                entity_type=extracted_entity.entity_type,
                canonical_name=extracted_entity.canonical_name,
                display_name=extracted_entity.display_name,
            )
        )
        counts["entities"] += 1
    db.flush()

    for mention in evidence.mentions:
        db.add(
            EntityMention(
                id=mention.id,
                entity_id=mention.entity_id,
                chunk_id=chunk_id,
                extraction_run_id=run_id,
                surface_text=mention.surface_text,
                start_char=mention.start_char,
                end_char=mention.end_char,
                confidence=mention.confidence,
            )
        )
        counts["mentions"] += 1
    for claim in evidence.claims:
        db.add(
            EvidenceClaim(
                id=claim.id,
                chunk_id=chunk_id,
                extraction_run_id=run_id,
                subject_entity_id=claim.subject_entity_id,
                claim_hash=claim.claim_hash,
                claim_text=claim.claim_text,
                predicate=claim.predicate,
                object_text=claim.object_text,
                polarity=claim.polarity,
                confidence=claim.confidence,
            )
        )
        counts["claims"] += 1
    for relationship in evidence.relationships:
        db.add(
            EvidenceRelationship(
                id=relationship.id,
                chunk_id=chunk_id,
                extraction_run_id=run_id,
                source_entity_id=relationship.source_entity_id,
                target_entity_id=relationship.target_entity_id,
                relationship_type=relationship.relationship_type,
                evidence_text=relationship.evidence_text,
                confidence=relationship.confidence,
            )
        )
        counts["relationships"] += 1