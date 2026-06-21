from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def make_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("SINGLE_USER_USERNAME", "admin")
    monkeypatch.setenv("SINGLE_USER_PASSWORD", "secret123")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")
    get_settings.cache_clear()
    return TestClient(create_app())


def test_login_sets_session_cookie(monkeypatch):
    client = make_client(monkeypatch)

    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "secret123"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert "ta_v2_session" in response.cookies


def test_login_rejects_wrong_password(monkeypatch):
    client = make_client(monkeypatch)

    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "bad-password"},
    )

    assert response.status_code == 401


def test_me_returns_current_user_after_login(monkeypatch):
    client = make_client(monkeypatch)
    client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {"id": "single-user", "username": "admin"}


def test_me_rejects_missing_session(monkeypatch):
    client = make_client(monkeypatch)

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_logout_clears_session_cookie(monkeypatch):
    client = make_client(monkeypatch)
    client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert response.cookies.get("ta_v2_session") is None

