def test_login_success(client):
    r = client.post("/api/auth/login", json={"email": "bhaskar@company.com"})
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert "Admin" in data["roles"]


def test_login_invalid(client):
    r = client.post("/api/auth/login", json={"email": "nobody@company.com"})
    assert r.status_code == 401


def test_documents_require_auth(client):
    r = client.get("/api/documents")
    assert r.status_code == 422 or r.status_code == 401


def test_login_rate_limit_returns_retry_after(client, monkeypatch):
    from backend.routers import auth_router
    from backend.services.rate_limit import RateLimitDecision

    monkeypatch.setattr(
        auth_router.rate_limiter,
        "check",
        lambda *args, **kwargs: RateLimitDecision(False, 17),
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "bhaskar@company.com"},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "17"
