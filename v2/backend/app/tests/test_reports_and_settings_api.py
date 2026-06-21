from collections.abc import Iterable

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.models import AppSettings
from app.db.session import SessionLocal
from app.main import create_app
from app.services import settings_service
from app.services.tradingagents_runner import RunExecutionInput, RunnerMessage
from app.workers.inprocess_manager import InProcessRunManager


class ReportingRunner:
    def run(self, run_input: RunExecutionInput) -> Iterable[RunnerMessage]:
        yield RunnerMessage(
            event_type="report_section_updated",
            payload={"section": "market_report"},
            report_section="market_report",
            report_title="Market Analysis",
            report_markdown="Market report body",
        )
        yield RunnerMessage(
            event_type="metric_updated",
            payload={},
            metrics={"llm_calls": 3, "tool_calls": 2, "tokens_in": 90, "tokens_out": 30},
        )


def clean_db() -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE TABLE run_evidence, rag_chunks, rag_documents, "
                "run_reports, run_metrics, run_events, runs, "
                "app_settings, users RESTART IDENTITY CASCADE"
            )
        )
        db.commit()


def make_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("SINGLE_USER_USERNAME", "admin")
    monkeypatch.setenv("SINGLE_USER_PASSWORD", "secret123")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("RUN_AUTOSTART", "true")
    get_settings.cache_clear()
    clean_db()
    manager = InProcessRunManager(runner=ReportingRunner(), run_inline=True)
    return TestClient(create_app(run_manager=manager))


def login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert response.status_code == 200


def create_completed_run(client: TestClient) -> str:
    response = client.post(
        "/api/runs",
        json={
            "ticker": "NVDA",
            "analysis_date": "2026-06-14",
            "asset_type": "stock",
            "selected_analysts": ["market"],
            "research_depth": 1,
            "llm_provider": "openai",
            "deep_think_llm": "gpt-5.5",
            "quick_think_llm": "gpt-5.4-mini",
            "output_language": "English",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_get_run_reports_returns_sections(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    run_id = create_completed_run(client)

    response = client.get(f"/api/runs/{run_id}/reports")

    assert response.status_code == 200
    assert response.json()["items"][0]["section"] == "market_report"
    assert response.json()["items"][0]["content_markdown"] == "Market report body"


def test_get_run_metrics_returns_latest_snapshot(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    run_id = create_completed_run(client)

    response = client.get(f"/api/runs/{run_id}/metrics")

    assert response.status_code == 200
    assert response.json()["llm_calls"] == 3
    assert response.json()["tool_calls"] == 2


def test_get_run_evidence_returns_items(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    run_id = create_completed_run(client)

    with SessionLocal() as db:
        from app.db.models import RagChunk, RagDocument, RunEvidence

        document = RagDocument(
            source_id="spy_evidence_api",
            ticker="SPY",
            scope="macro",
            source_type="fomc_statement",
            source_name="Federal Reserve",
            title="FOMC API Test",
            published_at=None,
            retrieved_at=None,
            url="https://example.test",
            tags=["fed"],
            confidence="high",
            license_note="public_source",
            document_metadata={},
            content_hash="hash",
        )
        db.add(document)
        db.flush()
        chunk = RagChunk(
            document_id=document.id,
            chunk_index=0,
            chunk_text="Rates stayed restrictive.",
            embedding=[1.0],
            token_estimate=3,
            chunk_metadata={},
        )
        db.add(chunk)
        db.flush()
        db.add(
            RunEvidence(
                run_id=run_id,
                chunk_id=chunk.id,
                agent_name="News Analyst",
                query="SPY macro",
                citation_key="E1",
                score=0.9,
                excerpt="Rates stayed restrictive.",
            )
        )
        db.commit()

    response = client.get(f"/api/runs/{run_id}/evidence")

    assert response.status_code == 200
    assert response.json()["items"][0]["source_title"] == "FOMC API Test"
    assert response.json()["items"][0]["citation_key"] == "E1"


def test_settings_defaults_and_update(monkeypatch):
    client = make_client(monkeypatch)
    login(client)

    defaults = client.get("/api/settings")
    assert defaults.status_code == 200
    assert defaults.json()["default_llm_provider"] == "deepseek"
    assert defaults.json()["default_deep_model"] == "deepseek-v4-pro"
    assert defaults.json()["default_quick_model"] == "deepseek-v4-flash"
    assert defaults.json()["default_output_language"] == "Chinese"
    assert defaults.json()["default_analysts"] == ["market", "social", "news", "fundamentals"]
    assert defaults.json()["deepseek_api_key"] == ""
    assert defaults.json()["fred_api_key"] == ""

    updated = client.put(
        "/api/settings",
        json={
            "default_llm_provider": "deepseek",
            "default_deep_model": "deepseek-reasoner",
            "default_quick_model": "deepseek-chat",
            "default_output_language": "Chinese",
            "default_analysts": ["market", "news"],
            "default_research_depth": 2,
            "default_checkpoint_enabled": True,
            "deepseek_api_key": "sk-test-deepseek",
            "fred_api_key": "fred-test-key",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["default_llm_provider"] == "deepseek"
    assert updated.json()["deepseek_api_key"] == "sk-test-deepseek"
    assert updated.json()["fred_api_key"] == "fred-test-key"
    assert client.get("/api/settings").json()["default_analysts"] == ["market", "news"]
    assert client.get("/api/settings").json()["deepseek_api_key"] == "sk-test-deepseek"


def test_get_settings_upgrades_legacy_openai_defaults(monkeypatch):
    client = make_client(monkeypatch)
    login(client)

    with SessionLocal() as db:
        settings = settings_service.get_or_create_settings(db, "admin")
        settings.default_llm_provider = "openai"
        settings.default_deep_model = "gpt-5.5"
        settings.default_quick_model = "gpt-5.4-mini"
        settings.default_output_language = "English"
        settings.default_analysts = ["news"]
        settings.default_research_depth = 1
        settings.default_checkpoint_enabled = True
        db.commit()

    response = client.get("/api/settings")

    assert response.status_code == 200
    assert response.json()["default_llm_provider"] == "deepseek"
    assert response.json()["default_deep_model"] == "deepseek-v4-pro"
    assert response.json()["default_quick_model"] == "deepseek-v4-flash"
    assert response.json()["default_analysts"] == ["market", "social", "news", "fundamentals"]


def test_get_settings_backfills_missing_api_keys_from_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-env")
    monkeypatch.setenv("FRED_API_KEY", "fred-from-env")
    client = make_client(monkeypatch)
    login(client)

    with SessionLocal() as db:
        settings = settings_service.get_or_create_settings(db, "admin")
        settings.deepseek_api_key = ""
        settings.fred_api_key = ""
        db.commit()

    response = client.get("/api/settings")

    assert response.status_code == 200
    assert response.json()["deepseek_api_key"] == "sk-from-env"
    assert response.json()["fred_api_key"] == "fred-from-env"


def test_update_settings_keeps_existing_api_keys_when_payload_is_blank(monkeypatch):
    client = make_client(monkeypatch)
    login(client)

    client.put(
        "/api/settings",
        json={
            "default_llm_provider": "deepseek",
            "default_deep_model": "deepseek-v4-pro",
            "default_quick_model": "deepseek-v4-flash",
            "default_output_language": "Chinese",
            "default_analysts": ["market", "news"],
            "default_research_depth": 2,
            "default_checkpoint_enabled": True,
            "deepseek_api_key": "sk-keep-me",
            "fred_api_key": "fred-keep-me",
        },
    )

    updated = client.put(
        "/api/settings",
        json={
            "default_llm_provider": "deepseek",
            "default_deep_model": "deepseek-reasoner",
            "default_quick_model": "deepseek-chat",
            "default_output_language": "Chinese",
            "default_analysts": ["market"],
            "default_research_depth": 1,
            "default_checkpoint_enabled": True,
            "deepseek_api_key": "",
            "fred_api_key": "",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["deepseek_api_key"] == "sk-keep-me"
    assert updated.json()["fred_api_key"] == "fred-keep-me"
