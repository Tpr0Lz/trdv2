from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import create_app


def clean_db() -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE TABLE run_reports, run_metrics, run_events, runs, "
                "app_settings, users RESTART IDENTITY CASCADE"
            )
        )
        db.commit()


def make_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("SINGLE_USER_USERNAME", "admin")
    monkeypatch.setenv("SINGLE_USER_PASSWORD", "secret123")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("RUN_AUTOSTART", "false")
    get_settings.cache_clear()
    clean_db()
    return TestClient(create_app())


def login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert response.status_code == 200


def run_payload() -> dict:
    return {
        "ticker": "NVDA",
        "analysis_date": "2026-06-14",
        "asset_type": "stock",
        "selected_analysts": ["market", "social", "news", "fundamentals"],
        "research_depth": 1,
        "llm_provider": "openai",
        "deep_think_llm": "gpt-5.5",
        "quick_think_llm": "gpt-5.4-mini",
        "output_language": "English",
    }


def test_create_run_requires_login(monkeypatch):
    client = make_client(monkeypatch)

    response = client.post("/api/runs", json=run_payload())

    assert response.status_code == 401


def test_create_run_persists_queued_run(monkeypatch):
    client = make_client(monkeypatch)
    login(client)

    response = client.post("/api/runs", json=run_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["ticker"] == "NVDA"
    assert body["analysis_date"] == "2026-06-14"
    assert body["status"] == "queued"
    assert body["checkpoint_thread_id"] == body["id"]
    assert body["config_snapshot"]["llm_provider"] == "openai"
    assert body["started_at"] is None
    assert body["completed_at"] is None


def test_create_macro_run_normalizes_selected_analysts_to_news(monkeypatch):
    client = make_client(monkeypatch)
    login(client)

    response = client.post(
        "/api/runs",
        json={
            **run_payload(),
            "ticker": "DGS10",
            "asset_type": "macro",
            "selected_analysts": ["market", "social", "news", "fundamentals"],
        },
    )

    assert response.status_code == 201
    assert response.json()["ticker"] == "DGS10"
    assert response.json()["asset_type"] == "macro"
    assert response.json()["selected_analysts"] == ["news"]


def test_list_runs_returns_newest_first(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    first = client.post("/api/runs", json={**run_payload(), "ticker": "AAPL"}).json()
    second = client.post("/api/runs", json={**run_payload(), "ticker": "MSFT"}).json()

    response = client.get("/api/runs")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [second["id"], first["id"]]


def test_get_run_returns_detail(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    created = client.post("/api/runs", json=run_payload()).json()

    response = client.get(f"/api/runs/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["selected_analysts"] == ["market", "social", "news", "fundamentals"]


def test_get_run_rejects_unknown_id(monkeypatch):
    client = make_client(monkeypatch)
    login(client)

    response = client.get("/api/runs/missing-run-id")

    assert response.status_code == 404
