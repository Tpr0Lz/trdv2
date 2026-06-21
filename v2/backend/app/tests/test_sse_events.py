import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import text
from threading import Thread

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import create_app
from app.api.runs import stream_run_events
from app.schemas.events import RunEventResponse
from app.services.run_event_service import append_run_event
from app.services.sse_broker import RunEventBroker


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


def create_run(client: TestClient) -> dict:
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
    return response.json()


def test_get_run_events_requires_login(monkeypatch):
    client = make_client(monkeypatch)

    response = client.get("/api/runs/not-logged-in/events")

    assert response.status_code == 401


def test_create_run_writes_run_created_event(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    run = create_run(client)

    response = client.get(f"/api/runs/{run['id']}/events")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["event_type"] == "run_created"
    assert items[0]["sequence"] == 1
    assert items[0]["payload"]["ticker"] == "NVDA"


def test_append_run_event_increments_sequence(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    run = create_run(client)

    with SessionLocal() as db:
        append_run_event(db, run["id"], "agent_started", {"agent": "Market Analyst"})
        append_run_event(db, run["id"], "agent_completed", {"agent": "Market Analyst"})
        db.commit()

    response = client.get(f"/api/runs/{run['id']}/events")

    assert response.status_code == 200
    assert [(item["event_type"], item["sequence"]) for item in response.json()["items"]] == [
        ("run_created", 1),
        ("agent_started", 2),
        ("agent_completed", 3),
    ]


def test_get_run_events_rejects_unknown_run(monkeypatch):
    client = make_client(monkeypatch)
    login(client)

    response = client.get("/api/runs/missing/events")

    assert response.status_code == 404


def test_stream_accepts_after_event_id_query(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    run = create_run(client)

    with SessionLocal() as db:
        append_run_event(db, run["id"], "agent_started", {"agent": "Market Analyst"})
        db.commit()

    events = client.get(f"/api/runs/{run['id']}/events").json()["items"]
    first_event_id = events[0]["id"]

    with SessionLocal() as db:
        response = stream_run_events(
            run["id"],
            last_event_id=None,
            after_event_id=first_event_id,
            db=db,
            username="admin",
        )
        first_block = asyncio.run(asyncio.wait_for(response.body_iterator.__anext__(), timeout=1))

    assert "event: agent_started" in first_block
    assert "event: run_created" not in first_block


def test_broker_delivers_events_published_from_worker_thread():
    broker = RunEventBroker()
    received: list[RunEventResponse] = []

    async def consume_once() -> None:
        async for event in broker.subscribe("run-1"):
            received.append(event)
            break

    async def exercise() -> None:
        task = __import__("asyncio").create_task(consume_once())
        await __import__("asyncio").sleep(0)

        event = RunEventResponse(
            id=1,
            run_id="run-1",
            event_type="report_section_streamed",
            agent_name="News Analyst",
            sequence=1,
            payload={"section": "news_report", "content_markdown": "partial"},
            created_at="2026-06-19T12:00:00Z",
        )
        worker = Thread(target=broker.publish, args=(event,))
        worker.start()
        worker.join(timeout=1)

        await __import__("asyncio").wait_for(task, timeout=1)

    __import__("asyncio").run(exercise())

    assert [event.event_type for event in received] == ["report_section_streamed"]
