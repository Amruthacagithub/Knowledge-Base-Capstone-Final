from datetime import datetime, timezone
from types import SimpleNamespace

from backend.routers import versions_router
from backend.services.temporal_retrieval import (
    TemporalDocumentUnavailable,
    VersionClaim,
    VersionComparison,
)


def test_temporal_api_is_disabled_by_default(client, admin_headers):
    response = client.get("/api/documents/document-1/versions", headers=admin_headers)

    assert response.status_code == 404


def test_version_history_returns_authorized_metadata(client, engineer_headers, monkeypatch):
    monkeypatch.setattr(versions_router, "TEMPORAL_API_ENABLED", True)
    monkeypatch.setattr(
        versions_router,
        "visible_version_history",
        lambda db, user_ctx, document_id: (_version("v1", 1, False), _version("v2", 2, True)),
    )

    response = client.get("/api/documents/document-1/versions", headers=engineer_headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["v1", "v2"]
    assert response.json()[1]["is_current"] is True


def test_hidden_and_missing_current_versions_share_404(client, engineer_headers, monkeypatch):
    monkeypatch.setattr(versions_router, "TEMPORAL_API_ENABLED", True)
    monkeypatch.setattr(
        versions_router,
        "current_visible_version",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            TemporalDocumentUnavailable("Document not found")
        ),
    )

    for document_id in ("hidden", "missing"):
        response = client.get(
            f"/api/documents/{document_id}/versions/current",
            headers=engineer_headers,
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found"}


def test_version_diff_exposes_claim_changes_and_reviewable_conflicts(
    client,
    engineer_headers,
    monkeypatch,
):
    monkeypatch.setattr(versions_router, "TEMPORAL_API_ENABLED", True)
    comparison = VersionComparison(
        document_id="document-1",
        from_version_id="v1",
        to_version_id="v2",
        added=(_claim("new", "v2", "PTO is 20 days."),),
        removed=(_claim("old", "v1", "PTO is 15 days."),),
        unchanged=(),
    )
    monkeypatch.setattr(
        versions_router,
        "compare_visible_versions",
        lambda *args, **kwargs: comparison,
    )
    monkeypatch.setattr(
        versions_router,
        "detect_version_conflicts",
        lambda *args, **kwargs: (
            SimpleNamespace(
                id="conflict-1",
                claim_a_id="old",
                claim_b_id="new",
                conflict_type="value_change",
                status="candidate",
                confidence=0.9,
                rationale="Values differ across versions.",
            ),
        ),
    )

    response = client.get(
        "/api/documents/document-1/diff",
        headers=engineer_headers,
        params={"from_version_id": "v1", "to_version_id": "v2"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["added"][0]["document_version_id"] == "v2"
    assert body["removed"][0]["document_version_id"] == "v1"
    assert body["conflicts"][0]["status"] == "candidate"
    assert body["conflicts"][0]["conflict_type"] == "value_change"


def test_only_admin_can_review_conflict(
    client,
    engineer_headers,
    admin_headers,
    monkeypatch,
):
    monkeypatch.setattr(versions_router, "TEMPORAL_API_ENABLED", True)
    reviewed = SimpleNamespace(
        id="conflict-1",
        claim_a_id="old",
        claim_b_id="new",
        conflict_type="value_change",
        status="confirmed",
        confidence=0.9,
        rationale="Values differ.",
    )
    monkeypatch.setattr(
        versions_router,
        "review_conflict",
        lambda *args, **kwargs: reviewed,
    )

    forbidden = client.patch(
        "/api/documents/document-1/conflicts/conflict-1",
        headers=engineer_headers,
        json={"status": "confirmed"},
    )
    allowed = client.patch(
        "/api/documents/document-1/conflicts/conflict-1",
        headers=admin_headers,
        json={"status": "confirmed"},
    )

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "confirmed"


def _version(version_id, number, current):
    return SimpleNamespace(
        id=version_id,
        version_number=number,
        content_hash="a" * 64,
        file_type="markdown",
        uploaded_at=datetime(2026, number, 1, tzinfo=timezone.utc),
        effective_from=datetime(2026, number, 1, tzinfo=timezone.utc),
        effective_to=None,
        authority_level=50,
        is_current=current,
    )


def _claim(claim_id, version_id, text):
    return VersionClaim(
        claim_id=claim_id,
        claim_hash=(claim_id.encode().hex() + "0" * 64)[:64],
        claim_text=text,
        predicate="allows",
        object_text=text.split("is ")[-1].rstrip("."),
        polarity=True,
        document_version_id=version_id,
    )