from types import SimpleNamespace

from backend.services.auth import UserContext
from backend.services.graph_retrieval import retrieve_graph_candidates
from backend.services.graph_traversal import (
    EvidencePath,
    PathScore,
    RankedEvidencePath,
    TracedTraversalResult,
    TraversalEdge,
    TraversalResult,
)
from backend.services import graph_retrieval


USER = UserContext(
    user_id="graph-search-user",
    email="graph-search@example.com",
    department="Engineering",
    roles=["Employee", "Engineer"],
)


def _entity(entity_id, name):
    return SimpleNamespace(
        id=entity_id,
        canonical_name=name.casefold().replace(" ", "_"),
        display_name=name,
    )


def _traced_result(start_id):
    edge = TraversalEdge(
        relationship_id=f"rel-{start_id}",
        source_entity_id=start_id,
        target_entity_id="stripe",
        relationship_type="depends_on",
        chunk_id="chunk-1",
        document_id="document-1",
        document_version_id="version-1",
        document_title="Architecture",
        department="Engineering",
        source_entity_name="Billing Service",
        target_entity_name="Stripe",
        evidence_text="Billing Service depends on Stripe.",
        confidence=0.9,
        authority_level=80,
        effective_from=None,
    )
    path = EvidencePath(entity_ids=(start_id, "stripe"), edges=(edge,))
    ranked = RankedEvidencePath(
        path=path,
        score=PathScore(0.8, 0.9, 0.8, 0.5, 0.0, 0.79),
    )
    return TracedTraversalResult(
        traversal=TraversalResult(start_id, (path,), False),
        ranked_paths=(ranked,),
        trace_id=f"trace-{start_id}",
    )


def test_graph_retrieval_starts_only_from_visible_query_entities(monkeypatch):
    starts = []
    monkeypatch.setattr(
        graph_retrieval,
        "visible_entities",
        lambda db, user_ctx: [
            _entity("billing", "Billing Service"),
            _entity("visible-other", "Document Service"),
        ],
    )

    def fake_traverse(db, user_ctx, entity_id, query, **kwargs):
        starts.append(entity_id)
        return _traced_result(entity_id)

    monkeypatch.setattr(graph_retrieval, "traverse_rank_and_trace", fake_traverse)

    result = retrieve_graph_candidates(
        object(),
        USER,
        "How does Billing Service reach hidden Payroll Service through Stripe?",
    )

    assert starts == ["billing"]
    assert result.trace_ids == ("trace-billing",)
    assert result.candidates[0]["chunk_id"] == "chunk-1"
    assert "Payroll" not in result.candidates[0]["text"]
    assert result.candidates[0]["graph_paths"][0]["entities"] == [
        {"id": "billing", "name": "Billing Service"},
        {"id": "stripe", "name": "Stripe"},
    ]
    assert result.candidates[0]["graph_paths"][0]["relationships"][0]["type"] == "depends_on"


def test_graph_retrieval_returns_empty_when_no_visible_entity_matches(monkeypatch):
    monkeypatch.setattr(
        graph_retrieval,
        "visible_entities",
        lambda db, user_ctx: [_entity("billing", "Billing Service")],
    )
    monkeypatch.setattr(
        graph_retrieval,
        "traverse_rank_and_trace",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()),
    )

    result = retrieve_graph_candidates(object(), USER, "Payroll dependency path")

    assert result.candidates == ()
    assert result.trace_ids == ()