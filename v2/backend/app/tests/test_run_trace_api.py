from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.models import Run, User
from app.db.session import SessionLocal
from app.main import create_app
from app.services.run_event_service import append_run_event
from app.services.run_trace_service import build_run_trace


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


def create_run() -> str:
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
            status="running",
            config_snapshot={},
            selected_analysts=["news"],
            checkpoint_thread_id="trace-test-thread",
        )
        db.add(run)
        db.flush()
        append_run_event(db, run.id, "run_started", {"ticker": "SPY"})
        append_run_event(
            db,
            run.id,
            "agent_started",
            {"section": "news_report", "title": "News Analysis"},
            "News Analyst",
        )
        append_run_event(
            db,
            run.id,
            "agent_completed",
            {"section": "news_report", "title": "News Analysis"},
            "News Analyst",
        )
        db.commit()
        return run.id


def test_build_run_trace_converts_lifecycle_and_agent_events():
    clean_db()
    run_id = create_run()

    with SessionLocal() as db:
        items = build_run_trace(db, run_id)

    assert [item.event_type for item in items] == [
        "run_started",
        "agent_started",
        "agent_completed",
    ]
    assert items[0].title == "Run started"
    assert items[1].agent_name == "News Analyst"
    assert items[1].kind == "agent_execution"
    assert items[2].status == "completed"


def test_build_run_trace_groups_rag_evidence_by_agent():
    clean_db()
    run_id = create_run()

    with SessionLocal() as db:
        from app.db.models import RagChunk, RagDocument, RunEvidence

        document = RagDocument(
            source_id="trace_fomc",
            ticker="SPY",
            scope="macro",
            source_type="fomc_statement",
            source_name="Federal Reserve",
            title="FOMC Trace Source",
            published_at=None,
            retrieved_at=None,
            url="https://example.test",
            tags=["fed"],
            confidence="high",
            license_note="public_source",
            document_metadata={},
            content_hash="trace-hash",
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

        items = build_run_trace(db, run_id)

    evidence_items = [item for item in items if item.event_type == "rag_evidence_retrieved"]
    assert len(evidence_items) == 1
    assert evidence_items[0].agent_name == "News Analyst"
    assert evidence_items[0].metadata["citation_keys"] == ["E1"]
    assert evidence_items[0].metadata["source_titles"] == ["FOMC Trace Source"]


def test_build_run_trace_collapses_streaming_events_by_section():
    clean_db()
    run_id = create_run()

    with SessionLocal() as db:
        append_run_event(
            db,
            run_id,
            "report_section_streamed",
            {"section": "news_report", "content_markdown": "short"},
            "News Analyst",
        )
        append_run_event(
            db,
            run_id,
            "report_section_streamed",
            {"section": "news_report", "content_markdown": "longer text"},
            "News Analyst",
        )
        db.commit()

        items = build_run_trace(db, run_id)

    streaming_items = [item for item in items if item.event_type == "report_section_streamed"]
    assert len(streaming_items) == 1
    assert streaming_items[0].metadata["section"] == "news_report"
    assert streaming_items[0].metadata["char_count"] == len("longer text")


def test_build_run_trace_labels_tool_events():
    clean_db()
    run_id = create_run()

    with SessionLocal() as db:
        append_run_event(
            db,
            run_id,
            "tool_started",
            {"tool_name": "get_news", "input": "SPY"},
            "News Analyst",
        )
        append_run_event(
            db,
            run_id,
            "tool_completed",
            {"tool_name": "get_news", "output_preview": "3 articles"},
            "News Analyst",
        )
        db.commit()

        items = build_run_trace(db, run_id)

    tool_items = [item for item in items if item.kind == "tool_call"]
    assert [item.event_type for item in tool_items] == ["tool_started", "tool_completed"]
    assert tool_items[0].title == "Tool started"
    assert tool_items[0].summary == "get_news input: SPY"
    assert tool_items[1].status == "completed"


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


def test_get_run_trace_requires_login(monkeypatch):
    client = make_client(monkeypatch)

    response = client.get("/api/runs/missing/trace")

    assert response.status_code == 401


def test_get_run_trace_returns_items(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    run_id = create_run()

    response = client.get(f"/api/runs/{run_id}/trace")

    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["event_type"] == "run_started"
    assert items[1]["event_type"] == "agent_started"
