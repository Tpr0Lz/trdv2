from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.base import utc_now
from app.db.models import Run, RunMetric, RunReport, User
from app.db.session import SessionLocal
from app.main import create_app
from app.services.run_quality_service import build_run_quality


def clean_db() -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE TABLE run_evidence, rag_chunks, rag_documents, "
                "run_reports, run_metrics, run_events, runs, app_settings, users "
                "RESTART IDENTITY CASCADE"
            )
        )
        db.commit()


def create_quality_run(selected_analysts: list[str] | None = None) -> str:
    with SessionLocal() as db:
        user = db.get(User, "single-user")
        if user is None:
            user = User(id="single-user", username="admin", password_hash="hash")
            db.add(user)
            db.flush()
        run = Run(
            user_id=user.id,
            ticker="SPY",
            analysis_date=date(2026, 6, 20),
            asset_type="stock",
            status="completed",
            config_snapshot={},
            selected_analysts=selected_analysts or ["market", "news"],
            checkpoint_thread_id="quality-test-thread",
        )
        db.add(run)
        db.flush()
        db.add(
            RunReport(
                run_id=run.id,
                section="market_report",
                title="Market Analysis",
                content_markdown="Market sees broad participation [E1].",
                version=1,
            )
        )
        db.add(
            RunMetric(
                run_id=run.id,
                llm_calls=2,
                tool_calls=1,
                tokens_in=120,
                tokens_out=80,
                elapsed_seconds=11,
                analyst_wall_times={},
                updated_at=utc_now(),
            )
        )
        db.commit()
        return run.id


def test_build_run_quality_flags_missing_selected_report_and_missing_evidence():
    clean_db()
    run_id = create_quality_run()

    with SessionLocal() as db:
        quality = build_run_quality(db, run_id)

    assert quality.score < 100
    assert quality.status == "warning"
    checks = {check.id: check for check in quality.checks}
    assert checks["selected_reports_present"].title == "已选报告完整性"
    assert checks["selected_reports_present"].status == "warning"
    assert checks["selected_reports_present"].summary == "缺少 1 份已选 analyst 报告。"
    assert "news_report" in checks["selected_reports_present"].details["missing_sections"]
    assert checks["citation_keys_valid"].title == "引用键有效性"
    assert checks["citation_keys_valid"].status == "fail"
    assert checks["citation_keys_valid"].summary == "有 1 个引用键无法映射到证据。"
    assert checks["citation_keys_valid"].details["invalid_citations"] == ["E1"]


def test_build_run_quality_passes_when_reports_and_citations_are_complete():
    clean_db()
    run_id = create_quality_run()

    with SessionLocal() as db:
        from app.db.models import RagChunk, RagDocument, RunEvidence

        document = RagDocument(
            source_id="quality_fomc",
            ticker="SPY",
            scope="macro",
            source_type="fomc_statement",
            source_name="Federal Reserve",
            title="FOMC Quality Source",
            published_at=None,
            retrieved_at=None,
            url="https://example.test",
            tags=["fed"],
            confidence="high",
            license_note="public_source",
            document_metadata={},
            content_hash="quality-hash",
        )
        db.add(document)
        db.flush()
        chunk = RagChunk(
            document_id=document.id,
            chunk_index=0,
            chunk_text="Policy remains restrictive.",
            embedding=[1.0],
            token_estimate=4,
            chunk_metadata={},
        )
        db.add(chunk)
        db.flush()
        db.add(
            RunEvidence(
                run_id=run_id,
                chunk_id=chunk.id,
                agent_name="Market Analyst",
                query="SPY macro",
                citation_key="E1",
                score=0.9,
                excerpt="Policy remains restrictive.",
            )
        )
        db.add(
            RunReport(
                run_id=run_id,
                section="news_report",
                title="News Analysis",
                content_markdown="News confirms the same macro signal [E1].",
                version=1,
            )
        )
        db.commit()

        quality = build_run_quality(db, run_id)

    assert quality.score == 100
    assert quality.status == "pass"
    assert quality.checks[0].title == "已选报告完整性"
    assert quality.checks[0].summary == "所有已选 analyst 报告都已生成。"
    assert all(check.status == "pass" for check in quality.checks)


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


def test_get_run_quality_returns_score(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    run_id = create_quality_run()

    response = client.get(f"/api/runs/{run_id}/quality")

    assert response.status_code == 200
    assert response.json()["run_id"] == run_id
    assert response.json()["checks"][0]["id"] == "selected_reports_present"
