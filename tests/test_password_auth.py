from backend.database import SessionLocal
from backend.models import AuthSession, User
from backend.routers import auth_router
from backend.services.auth import authenticate, hash_password


def test_password_mode_uses_argon2_and_generic_failures(client, monkeypatch):
    monkeypatch.setattr(auth_router, "AUTH_MODE", "password")
    db = SessionLocal()
    try:
        user = db.get(User, "bhaskar")
        user.password_hash = hash_password("correct horse battery staple")
        db.commit()
    finally:
        db.close()

    success = client.post(
        "/api/auth/login",
        json={
            "email": "BHASKAR@COMPANY.COM",
            "password": "correct horse battery staple",
        },
    )
    wrong = client.post(
        "/api/auth/login",
        json={"email": "bhaskar@company.com", "password": "wrong password"},
    )
    missing = client.post(
        "/api/auth/login",
        json={"email": "missing@company.com", "password": "wrong password"},
    )

    assert success.status_code == 200
    assert success.json()["expires_in"] == 1800
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json() == {"detail": "Invalid email or password"}
    db = SessionLocal()
    try:
        assert db.query(AuthSession).filter_by(user_id="bhaskar").count() >= 1
    finally:
        db.close()


def test_logout_revokes_server_side_session(client, admin_headers):
    token = admin_headers["Authorization"].removeprefix("Bearer ")

    assert authenticate(token) is not None
    response = client.post("/api/auth/logout", headers=admin_headers)

    assert response.status_code == 204
    assert authenticate(token) is None