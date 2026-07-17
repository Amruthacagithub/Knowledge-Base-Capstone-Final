from backend.services.evidence_extractor import (
    EXTRACTOR_NAME,
    EVIDENCE_SCHEMA_VERSION,
    extract_chunk_evidence,
    extraction_run_id,
)
from backend.services.chunker import chunk_text


TEXT = (
    "Incident INC-5023 affected Billing Service. "
    "Billing Service depends on Stripe Gateway. "
    "On-Call Runbook mitigates INC-5023."
)


def test_extraction_is_deterministic_and_grounded_in_exact_spans():
    first = extract_chunk_evidence("chunk-1", TEXT)
    second = extract_chunk_evidence("chunk-1", TEXT)

    assert first == second
    assert EXTRACTOR_NAME == "trust-rag-engineering-rules"
    assert EVIDENCE_SCHEMA_VERSION == "1.0"
    assert all(
        TEXT[mention.start_char : mention.end_char] == mention.surface_text
        for mention in first.mentions
    )
    assert {entity.canonical_name for entity in first.entities} == {
        "inc_5023",
        "billing_service",
        "stripe_gateway",
        "on_call_runbook",
    }


def test_extraction_emits_only_sentence_evidenced_relationships_and_claims():
    evidence = extract_chunk_evidence("chunk-1", TEXT)

    assert [relationship.relationship_type for relationship in evidence.relationships] == [
        "affected",
        "depends_on",
        "mitigates",
    ]
    assert [claim.predicate for claim in evidence.claims] == [
        "affected",
        "depends_on",
        "mitigates",
    ]
    assert all(
        relationship.evidence_text in TEXT
        for relationship in evidence.relationships
    )
    assert all(claim.claim_text in TEXT for claim in evidence.claims)


def test_extraction_does_not_invent_relations_without_a_lexical_link():
    evidence = extract_chunk_evidence(
        "chunk-2",
        "Billing Service and Stripe Gateway are listed for reference.",
    )

    assert len(evidence.entities) == 2
    assert evidence.relationships == ()


def test_extraction_configuration_has_stable_run_identity():
    first_run_id = extraction_run_id("version-1")
    repeated_run_id = extraction_run_id("version-1")

    assert first_run_id == repeated_run_id
    assert first_run_id != extraction_run_id("version-2")


def test_service_map_does_not_create_cross_row_relationships():
    text = (
        "Clients → Kong Gateway → User Service\n"
        "         → Billing Service → Stripe\n"
        "         → Document Service → Elasticsearch, S3\n"
        "         → Notification Service → SendGrid, Slack"
    )
    chunk = chunk_text(text)[0]
    evidence = extract_chunk_evidence("service-map", chunk)
    names = {entity.id: entity.canonical_name for entity in evidence.entities}
    relationships = {
        (
            names[relationship.source_entity_id],
            relationship.relationship_type,
            names[relationship.target_entity_id],
        )
        for relationship in evidence.relationships
    }

    assert relationships == {
        ("kong_gateway", "routes_to", "user_service"),
        ("billing_service", "depends_on", "stripe"),
        ("document_service", "depends_on", "elasticsearch"),
        ("document_service", "depends_on", "s3"),
        ("notification_service", "depends_on", "sendgrid"),
        ("notification_service", "depends_on", "slack"),
    }