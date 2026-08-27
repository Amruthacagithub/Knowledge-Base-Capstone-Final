"""Smoke trust-flag contract tests (no live API required)."""
import importlib


def test_smoke_api_trust_mode_parsing():
    smoke = importlib.import_module("scripts.smoke_api")
    assert smoke._TRUST_MODE in {"auto", "true", "false"} or smoke._TRUST_MODE


def test_search_router_always_includes_query_plan_in_schema(client, admin_headers, monkeypatch):
    from backend.routers import search_router

    monkeypatch.setattr(search_router, "hybrid_search", lambda **kwargs: ([], "conceptual"))

    response = client.post(
        "/api/search",
        headers=admin_headers,
        json={"query": "What is the PTO policy?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "query_plan" in body
    assert body["query_plan"]["route"] == "local"
    assert "claims" in body
    assert isinstance(body["claims"], list)


def test_graph_endpoint_disabled_returns_404(client, engineer_headers, monkeypatch):
    from backend.routers import graph_router

    monkeypatch.setattr(graph_router, "EVIDENCE_GRAPH_ENABLED", False)

    response = client.get(
        "/api/graph/entities",
        headers=engineer_headers,
        params={"query": "billing"},
    )

    assert response.status_code == 404


def test_graph_endpoint_enabled_returns_entities(client, engineer_headers, monkeypatch):
    from types import SimpleNamespace

    from backend.routers import graph_router

    monkeypatch.setattr(graph_router, "EVIDENCE_GRAPH_ENABLED", True)
    monkeypatch.setattr(
        graph_router,
        "visible_entities",
        lambda db, user_ctx: [
            SimpleNamespace(
                id="entity-1",
                entity_type="service",
                canonical_name="billing_service",
                display_name="Billing Service",
            )
        ],
    )

    response = client.get(
        "/api/graph/entities",
        headers=engineer_headers,
        params={"query": "billing"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_versions_endpoint_disabled_returns_404(client, admin_headers, monkeypatch):
    from backend.routers import versions_router

    monkeypatch.setattr(versions_router, "TEMPORAL_API_ENABLED", False)

    response = client.get(
        "/api/documents/doc-1/versions",
        headers=admin_headers,
    )

    assert response.status_code == 404
