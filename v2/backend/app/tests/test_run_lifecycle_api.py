from collections.abc import Iterable

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.models import Run
from app.db.session import SessionLocal
from app.main import create_app
from app.services.tradingagents_runner import RunExecutionInput, RunnerMessage
from app.workers.inprocess_manager import InProcessRunManager


class CompletingRunner:
    def run(self, run_input: RunExecutionInput) -> Iterable[RunnerMessage]:
        yield RunnerMessage(event_type="metric_updated", payload={}, metrics={"llm_calls": 1})


def clean_db() -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE TABLE run_reports, run_metrics, run_events, runs, "
                "app_settings, users RESTART IDENTITY CASCADE"
            )
        )
        db.commit()


def make_client(monkeypatch, run_autostart: bool) -> TestClient:
    monkeypatch.setenv("SINGLE_USER_USERNAME", "admin")
    monkeypatch.setenv("SINGLE_USER_PASSWORD", "secret123")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("RUN_AUTOSTART", "true" if run_autostart else "false")
    get_settings.cache_clear()
    clean_db()
    manager = InProcessRunManager(runner=CompletingRunner(), run_inline=True)
    return TestClient(create_app(run_manager=manager))


def login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert response.status_code == 200


def payload() -> dict:
    return {
        "ticker": "NVDA",
        "analysis_date": "2026-06-14",
        "asset_type": "stock",
        "selected_analysts": ["market"],
        "research_depth": 1,
        "llm_provider": "openai",
        "deep_think_llm": "gpt-5.5",
        "quick_think_llm": "gpt-5.4-mini",
        "output_language": "English",
    }


def test_create_run_autostarts_background_manager(monkeypatch):
    client = make_client(monkeypatch, run_autostart=True)
    login(client)

    created = client.post("/api/runs", json=payload()).json()
    detail = client.get(f"/api/runs/{created['id']}").json()

    assert detail["status"] == "completed"


def test_resume_interrupted_run_uses_manager(monkeypatch):
    client = make_client(monkeypatch, run_autostart=False)
    login(client)
    created = client.post("/api/runs", json=payload()).json()
    with SessionLocal() as db:
        run = db.get(Run, created["id"])
        assert run is not None
        run.status = "interrupted"
        db.commit()

    response = client.post(f"/api/runs/{created['id']}/resume")

    assert response.status_code == 200
    assert client.get(f"/api/runs/{created['id']}").json()["status"] == "completed"


def test_pause_queued_run(monkeypatch):
    client = make_client(monkeypatch, run_autostart=False)
    login(client)
    created = client.post("/api/runs", json=payload()).json()

    response = client.post(f"/api/runs/{created['id']}/pause")

    assert response.status_code == 200
    assert response.json()["status"] == "paused"


def test_resume_paused_run_uses_manager(monkeypatch):
    client = make_client(monkeypatch, run_autostart=False)
    login(client)
    created = client.post("/api/runs", json=payload()).json()
    pause_response = client.post(f"/api/runs/{created['id']}/pause")
    assert pause_response.status_code == 200

    response = client.post(f"/api/runs/{created['id']}/resume")

    assert response.status_code == 200
    assert client.get(f"/api/runs/{created['id']}").json()["status"] == "completed"


def test_cancel_queued_run(monkeypatch):
    client = make_client(monkeypatch, run_autostart=False)
    login(client)
    created = client.post("/api/runs", json=payload()).json()

    response = client.post(f"/api/runs/{created['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
