from types import SimpleNamespace
from datetime import datetime, timezone

from backend.routers import graph_router
from backend.services.graph_traversal import (
    EvidencePath,
    GraphEntityUnavailable,
    PathScore,
    RankedEvidencePath,
    TraversalEdge,
    TraversalResult,
    TracedTraversalResult,
)


def test_graph_api_is_disabled_by_default(client, admin_headers):
    response = client.get(
        "/api/graph/entities",
        headers=admin_headers,
        params={"query": "billing"},
    )

    assert response.status_code == 404


def test_entity_search_returns_only_authorized_service_results(
    client,
    engineer_headers,
    monkeypatch,
):
    monkeypatch.setattr(graph_router, "EVIDENCE_GRAPH_ENABLED", True)
    monkeypatch.setattr(
        graph_router,
        "visible_entities",
        lambda db, user_ctx: [
            SimpleNamespace(
                id="billing",
                entity_type="system",
                canonical_name="billing_service",
                display_name="Billing Service",
            ),
            SimpleNamespace(
                id="stripe",
                entity_type="system",
                canonical_name="stripe",
                display_name="Stripe",
            ),
        ],
    )

    response = client.get(
        "/api/graph/entities",
        headers=engineer_headers,
        params={"query": "billing"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "billing",
            "entity_type": "system",
            "canonical_name": "billing_service",
            "display_name": "Billing Service",
        }
    ]


def test_hidden_and_missing_path_starts_share_the_same_404(
    client,
    engineer_headers,
    monkeypatch,
):
    monkeypatch.setattr(graph_router, "EVIDENCE_GRAPH_ENABLED", True)
    monkeypatch.setattr(
        graph_router,
        "traverse_rank_and_trace",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            GraphEntityUnavailable("Entity not found")
        ),
    )

    for entity_id in ("hidden-entity", "missing-entity"):
        response = client.get(
            f"/api/graph/entities/{entity_id}/paths",
            headers=engineer_headers,
            params={"query": "dependency"},
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Entity not found"}


def test_authorized_path_response_contains_evidence_score_and_trace(
    client,
    engineer_headers,
    monkeypatch,
):
    monkeypatch.setattr(graph_router, "EVIDENCE_GRAPH_ENABLED", True)
    edge = TraversalEdge(
        relationship_id="relationship-1",
        source_entity_id="billing",
        target_entity_id="stripe",
        relationship_type="depends_on",
        chunk_id="chunk-1",
        document_id="document-1",
        document_version_id="version-1",
        document_title="Architecture Overview",
        department="Engineering",
        source_entity_name="Billing Service",
        target_entity_name="Stripe",
        evidence_text="Billing Service depends on Stripe.",
        confidence=0.9,
        authority_level=80,
        effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    path = EvidencePath(entity_ids=("billing", "stripe"), edges=(edge,))
    ranked = RankedEvidencePath(
        path=path,
        score=PathScore(
            relevance=1.0,
            coherence=0.9,
            authority=0.8,
            freshness=0.7,
            conflict_penalty=0.0,
            total=0.81,
        ),
    )
    monkeypatch.setattr(
        graph_router,
        "traverse_rank_and_trace",
        lambda *args, **kwargs: TracedTraversalResult(
            traversal=TraversalResult(
                start_entity_id="billing",
                paths=(path,),
                truncated=False,
            ),
            ranked_paths=(ranked,),
            trace_id="trace-1",
        ),
    )

    response = client.get(
        "/api/graph/entities/billing/paths",
        headers=engineer_headers,
        params={"query": "billing stripe dependency"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == "trace-1"
    assert body["paths"][0]["edges"][0]["evidence_text"] == edge.evidence_text
    assert body["paths"][0]["score"]["total"] == 0.81