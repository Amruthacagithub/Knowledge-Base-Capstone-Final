def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "components" in data
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-request-id"]


def test_untrusted_host_is_rejected(client):
    response = client.get("/api/health", headers={"Host": "attacker.example"})

    assert response.status_code == 400
