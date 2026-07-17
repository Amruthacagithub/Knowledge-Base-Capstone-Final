from datetime import datetime, timezone

import pytest

from backend.models import (
    Chunk,
    Document,
    DocumentVersion,
    Entity,
    EntityMention,
    EvidenceRelationship,
    ExtractionRun,
    RetrievalTrace,
)
from backend.services.auth import UserContext
from backend.services.graph_traversal import (
    GraphEntityUnavailable,
    PathScoreWeights,
    rank_evidence_paths,
    traverse_rank_and_trace,
    traverse_visible_graph,
)


def test_traversal_drops_restricted_edge_before_expansion(db_session):
    _edge(db_session, "public-ab", "entity-a", "entity-b", "public", "Engineering")
    _edge(db_session, "restricted-bc", "entity-b", "entity-c", "restricted", "HR")
    _edge(db_session, "public-ba-cycle", "entity-b", "entity-a", "public", "Engineering")

    engineer = _user("Engineer")
    admin = _user("Admin")

    engineer_result = traverse_visible_graph(
        db_session,
        engineer,
        "entity-a",
        max_depth=3,
    )
    admin_result = traverse_visible_graph(
        db_session,
        admin,
        "entity-a",
        max_depth=3,
    )

    assert [path.entity_ids for path in engineer_result.paths] == [
        ("entity-a", "entity-b")
    ]
    assert [path.entity_ids for path in admin_result.paths] == [
        ("entity-a", "entity-b"),
        ("entity-a", "entity-b", "entity-c"),
    ]
    assert all("entity-c" not in path.entity_ids for path in engineer_result.paths)
    assert all(len(set(path.entity_ids)) == len(path.entity_ids) for path in admin_result.paths)
    assert engineer_result.paths[0].edges[0].chunk_id == "public-ab-chunk"
    assert engineer_result.paths[0].edges[0].evidence_text == "entity-a depends on entity-b"


def test_hidden_start_is_indistinguishable_from_missing_entity(db_session):
    _edge(db_session, "restricted-de", "entity-d", "entity-e", "restricted", "HR")
    engineer = _user("Engineer")

    with pytest.raises(GraphEntityUnavailable, match="Entity not found"):
        traverse_visible_graph(db_session, engineer, "entity-d")
    with pytest.raises(GraphEntityUnavailable, match="Entity not found"):
        traverse_visible_graph(db_session, engineer, "does-not-exist")


def test_traversal_limits_are_enforced_and_report_truncation(db_session):
    _edge(db_session, "limit-ab", "limit-a", "limit-b", "public", "Engineering")
    _edge(db_session, "limit-ac", "limit-a", "limit-c", "public", "Engineering")

    result = traverse_visible_graph(
        db_session,
        _user("Engineer"),
        "limit-a",
        max_depth=1,
        max_paths=1,
    )

    assert len(result.paths) == 1
    assert result.truncated is True
    engineer = _user("Engineer")
    with pytest.raises(ValueError, match="max_depth"):
        traverse_visible_graph(db_session, engineer, "limit-a", max_depth=4)
    with pytest.raises(ValueError, match="max_paths"):
        traverse_visible_graph(db_session, engineer, "limit-a", max_paths=101)


def test_path_ranking_is_transparent_and_conflict_aware(db_session):
    _edge(db_session, "rank-billing", "rank-a", "rank-billing", "public", "Engineering")
    _edge(db_session, "rank-unrelated", "rank-a", "rank-other", "public", "Engineering")
    result = traverse_visible_graph(db_session, _user("Engineer"), "rank-a", max_depth=1)

    ranked = rank_evidence_paths(
        result.paths,
        "billing dependency",
        now=datetime(2026, 7, 26, tzinfo=timezone.utc),
    )
    conflicted = rank_evidence_paths(
        result.paths,
        "billing dependency",
        conflicting_relationship_ids={"rank-billing-relationship"},
        now=datetime(2026, 7, 26, tzinfo=timezone.utc),
    )

    assert ranked[0].path.entity_ids[-1] == "rank-billing"
    assert ranked[0].score.relevance > ranked[1].score.relevance
    assert ranked[0].score.coherence == 1.0
    assert ranked[0].score.authority == 0.5
    billing_after_penalty = next(
        item for item in conflicted if item.path.entity_ids[-1] == "rank-billing"
    )
    assert billing_after_penalty.score.conflict_penalty == 1.0
    assert billing_after_penalty.score.total < ranked[0].score.total


def test_path_relevance_does_not_credit_unreached_evidence_entities(db_session):
    _edge(
        db_session,
        "rank-first",
        "deploy-start",
        "deploy-middle",
        "public",
        "Engineering",
    )
    _edge(
        db_session,
        "rank-second",
        "deploy-middle",
        "final-target",
        "public",
        "Engineering",
    )
    result = traverse_visible_graph(
        db_session,
        _user("Engineer"),
        "deploy-start",
        max_depth=2,
    )

    ranked = rank_evidence_paths(result.paths, "reach final target")

    assert ranked[0].path.entity_ids == (
        "deploy-start",
        "deploy-middle",
        "final-target",
    )
    assert ranked[0].score.relevance > ranked[1].score.relevance


def test_path_ranking_rejects_invalid_weights():
    invalid_weights = PathScoreWeights(relevance=0.5)
    with pytest.raises(ValueError, match="sum to 1.0"):
        rank_evidence_paths(
            (),
            "query",
            weights=invalid_weights,
        )


def test_trace_contains_only_authorized_ids_and_scores(db_session):
    _edge(db_session, "trace-public", "trace-a", "trace-b", "public", "Engineering")
    _edge(db_session, "trace-hidden", "trace-b", "trace-secret", "restricted", "HR")

    result = traverse_rank_and_trace(
        db_session,
        _user("Engineer"),
        "trace-a",
        "trace dependency",
        max_depth=3,
    )
    trace = db_session.get(RetrievalTrace, result.trace_id)
    serialized = str(trace.paths_json)

    assert trace.returned_paths == 1
    assert trace.query_text.startswith("sha256:")
    assert "trace dependency" not in trace.query_text
    assert trace.paths_json[0]["entity_ids"] == ["trace-a", "trace-b"]
    assert "trace-secret" not in serialized
    assert "trace-hidden" not in serialized
    assert "depends on" not in serialized
    assert set(trace.paths_json[0]) == {
        "entity_ids",
        "relationship_ids",
        "chunk_ids",
        "document_ids",
        "score",
    }


def _edge(db_session, prefix, source_id, target_id, classification, department):
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
        content_hash=(prefix.encode().hex() + "0" * 64)[:64],
        storage_uri=f"file:///tmp/{prefix}.md",
        file_type="markdown",
        file_size_bytes=20,
        is_current=True,
    )
    chunk = Chunk(
        id=f"{prefix}-chunk",
        document_version=version,
        sequence_index=0,
        text_content=f"{source_id} depends on {target_id}",
        content_hash=(prefix.encode().hex() + "1" * 64)[:64],
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
    source = db_session.get(Entity, source_id) or Entity(
        id=source_id,
        entity_type="system",
        canonical_name=source_id,
        display_name=source_id,
    )
    target = db_session.get(Entity, target_id) or Entity(
        id=target_id,
        entity_type="system",
        canonical_name=target_id,
        display_name=target_id,
    )
    db_session.add_all([document, version, chunk, run, source, target])
    db_session.flush()
    for index, entity in enumerate((source, target)):
        display_name = str(entity.display_name)
        db_session.add(
            EntityMention(
                id=f"{prefix}-mention-{index}",
                entity_id=entity.id,
                chunk_id=chunk.id,
                extraction_run_id=run.id,
                surface_text=display_name,
                start_char=index * 20,
                end_char=index * 20 + len(display_name),
                confidence=1.0,
            )
        )
    db_session.add(
        EvidenceRelationship(
            id=f"{prefix}-relationship",
            chunk_id=chunk.id,
            extraction_run_id=run.id,
            source_entity_id=source.id,
            target_entity_id=target.id,
            relationship_type="depends_on",
            evidence_text=chunk.text_content,
            confidence=1.0,
        )
    )
    db_session.flush()


def _user(role):
    return UserContext(
        user_id=f"test-{role}",
        email=f"{role.lower()}@example.com",
        department="Engineering",
        roles=["Employee", role],
    )