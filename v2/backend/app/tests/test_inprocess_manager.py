from collections.abc import Iterable
from threading import Event
import time

from sqlalchemy import text

from app.db.models import Run, RunMetric, RunReport
from app.db.session import SessionLocal
from app.schemas.runs import RunCreateRequest
from app.services.settings_service import get_or_create_settings
from app.services.run_event_service import append_run_event
from app.services.run_service import create_run
from app.services.tradingagents_runner import RunExecutionInput, RunnerMessage
from app.workers.inprocess_manager import InProcessRunManager


def clean_db() -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE TABLE run_reports, run_metrics, run_events, runs, "
                "app_settings, users RESTART IDENTITY CASCADE"
            )
        )
        db.commit()


def run_payload() -> RunCreateRequest:
    return RunCreateRequest(
        ticker="NVDA",
        analysis_date="2026-06-14",
        asset_type="stock",
        selected_analysts=["market"],
        research_depth=1,
        llm_provider="openai",
        deep_think_llm="gpt-5.5",
        quick_think_llm="gpt-5.4-mini",
        output_language="English",
    )


class FakeRunner:
    def run(self, run_input: RunExecutionInput) -> Iterable[RunnerMessage]:
        assert run_input.checkpoint_thread_id == run_input.run_id
        yield RunnerMessage(
            event_type="agent_started",
            agent_name="Market Analyst",
            payload={"agent": "Market Analyst"},
        )
        yield RunnerMessage(
            event_type="report_section_streamed",
            agent_name="Market Analyst",
            payload={"section": "market_report", "is_partial": True},
            report_section="market_report",
            report_title="Market Analysis",
            report_markdown="Streaming draft",
        )
        yield RunnerMessage(
            event_type="report_section_updated",
            agent_name="Market Analyst",
            payload={"section": "market_report"},
            report_section="market_report",
            report_title="Market Analysis",
            report_markdown="Market report body",
        )
        yield RunnerMessage(
            event_type="metric_updated",
            payload={"llm_calls": 2},
            metrics={
                "llm_calls": 2,
                "tool_calls": 3,
                "tokens_in": 100,
                "tokens_out": 40,
                "elapsed_seconds": 7,
                "analyst_wall_times": {"market": 1.2},
            },
        )


class RuntimeKeyCaptureRunner:
    def __init__(self) -> None:
        self.runtime_api_keys: dict[str, str] | None = None
        self.resume_from_checkpoint: bool | None = None
        self.prior_streamed_sections: dict[str, str] | None = None

    def run(self, run_input: RunExecutionInput) -> Iterable[RunnerMessage]:
        self.runtime_api_keys = run_input.runtime_api_keys
        self.resume_from_checkpoint = run_input.resume_from_checkpoint
        self.prior_streamed_sections = run_input.prior_streamed_sections
        yield RunnerMessage(
            event_type="metric_updated",
            payload={"llm_calls": 0},
            metrics={
                "llm_calls": 0,
                "tool_calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "elapsed_seconds": 0,
                "analyst_wall_times": {},
            },
        )


class BlockingRunner:
    def __init__(self) -> None:
        self.first_run_started = Event()
        self.release_first_run = Event()
        self.started_run_ids: list[str] = []

    def run(self, run_input: RunExecutionInput) -> Iterable[RunnerMessage]:
        self.started_run_ids.append(run_input.run_id)
        if len(self.started_run_ids) == 1:
            self.first_run_started.set()
            self.release_first_run.wait(timeout=5)
        yield RunnerMessage(
            event_type="metric_updated",
            payload={"llm_calls": 0},
            metrics={
                "llm_calls": 0,
                "tool_calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "elapsed_seconds": 0,
                "analyst_wall_times": {},
            },
        )


class PausableRunner:
    def __init__(self) -> None:
        self.after_first_message = Event()
        self.allow_second_message = Event()

    def run(self, run_input: RunExecutionInput) -> Iterable[RunnerMessage]:
        yield RunnerMessage(
            event_type="metric_updated",
            payload={"llm_calls": 1},
            metrics={
                "llm_calls": 1,
                "tool_calls": 0,
                "tokens_in": 1,
                "tokens_out": 1,
                "elapsed_seconds": 1,
                "analyst_wall_times": {},
            },
        )
        self.after_first_message.set()
        self.allow_second_message.wait(timeout=5)
        yield RunnerMessage(
            event_type="metric_updated",
            payload={"llm_calls": 2},
            metrics={
                "llm_calls": 2,
                "tool_calls": 0,
                "tokens_in": 2,
                "tokens_out": 2,
                "elapsed_seconds": 2,
                "analyst_wall_times": {},
            },
        )


class SafePointRunner:
    def __init__(self) -> None:
        self.after_partial = Event()
        self.allow_completion = Event()

    def run(self, run_input: RunExecutionInput) -> Iterable[RunnerMessage]:
        yield RunnerMessage(
            event_type="report_section_streamed",
            agent_name="Market Analyst",
            payload={"section": "market_report", "content_markdown": "partial", "is_partial": True},
            report_section="market_report",
            report_title="Market Analysis",
            report_markdown="partial",
        )
        self.after_partial.set()
        self.allow_completion.wait(timeout=5)
        yield RunnerMessage(
            event_type="report_section_updated",
            agent_name="Market Analyst",
            payload={"section": "market_report", "content_markdown": "final", "is_partial": False},
            report_section="market_report",
            report_title="Market Analysis",
            report_markdown="final",
        )


class AgentBoundaryPauseRunner:
    def __init__(self) -> None:
        self.after_market_stream = Event()
        self.allow_switch = Event()

    def run(self, run_input: RunExecutionInput) -> Iterable[RunnerMessage]:
        yield RunnerMessage(
            event_type="agent_started",
            agent_name="Market Analyst",
            payload={"section": "market_report"},
            report_section="market_report",
            report_title="Market Analysis",
        )
        yield RunnerMessage(
            event_type="report_section_streamed",
            agent_name="Market Analyst",
            payload={"section": "market_report", "content_markdown": "market body", "is_partial": True},
            report_section="market_report",
            report_title="Market Analysis",
            report_markdown="market body",
        )
        self.after_market_stream.set()
        self.allow_switch.wait(timeout=5)
        yield RunnerMessage(
            event_type="agent_completed",
            agent_name="Market Analyst",
            payload={"section": "market_report"},
            report_section="market_report",
            report_title="Market Analysis",
        )
        yield RunnerMessage(
            event_type="agent_started",
            agent_name="News Analyst",
            payload={"section": "news_report"},
            report_section="news_report",
            report_title="News Analysis",
        )
        yield RunnerMessage(
            event_type="report_section_streamed",
            agent_name="News Analyst",
            payload={"section": "news_report", "content_markdown": "news body", "is_partial": True},
            report_section="news_report",
            report_title="News Analysis",
            report_markdown="news body",
        )


class ResumeOrderRunner:
    def __init__(self) -> None:
        self.run_calls = 0

    def run(self, run_input: RunExecutionInput) -> Iterable[RunnerMessage]:
        self.run_calls += 1
        if self.run_calls == 1:
            yield RunnerMessage(
                event_type="agent_started",
                agent_name="Market Analyst",
                payload={"section": "market_report"},
                report_section="market_report",
                report_title="Market Analysis",
            )
            yield RunnerMessage(
                event_type="report_section_streamed",
                agent_name="Market Analyst",
                payload={"section": "market_report", "content_markdown": "market body", "is_partial": True},
                report_section="market_report",
                report_title="Market Analysis",
                report_markdown="market body",
            )
            yield RunnerMessage(
                event_type="agent_completed",
                agent_name="Market Analyst",
                payload={"section": "market_report"},
                report_section="market_report",
                report_title="Market Analysis",
            )
            return

        yield RunnerMessage(
            event_type="agent_started",
            agent_name="Sentiment Analyst",
            payload={"section": "sentiment_report"},
            report_section="sentiment_report",
            report_title="Sentiment Analysis",
        )
        yield RunnerMessage(
            event_type="report_section_streamed",
            agent_name="Sentiment Analyst",
            payload={
                "section": "sentiment_report",
                "content_markdown": "sentiment body",
                "is_partial": True,
            },
            report_section="sentiment_report",
            report_title="Sentiment Analysis",
            report_markdown="sentiment body",
        )
        yield RunnerMessage(
            event_type="agent_completed",
            agent_name="Sentiment Analyst",
            payload={"section": "sentiment_report"},
            report_section="sentiment_report",
            report_title="Sentiment Analysis",
        )
        yield RunnerMessage(
            event_type="agent_started",
            agent_name="News Analyst",
            payload={"section": "news_report"},
            report_section="news_report",
            report_title="News Analysis",
        )
        yield RunnerMessage(
            event_type="report_section_streamed",
            agent_name="News Analyst",
            payload={"section": "news_report", "content_markdown": "news body", "is_partial": True},
            report_section="news_report",
            report_title="News Analysis",
            report_markdown="news body",
        )


def create_queued_run() -> str:
    with SessionLocal() as db:
        run = create_run(db, "admin", run_payload())
        return run.id


def wait_for_run_status(run_id: str, expected_status: str, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with SessionLocal() as db:
            run = db.get(Run, run_id)
            if run is not None and run.status == expected_status:
                return
        time.sleep(0.05)
    raise AssertionError(f"Run {run_id} did not reach status {expected_status}")


def test_manager_runs_queued_run_to_completion():
    clean_db()
    run_id = create_queued_run()
    manager = InProcessRunManager(runner=FakeRunner(), run_inline=True)

    manager.start_run(run_id)

    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        assert run.status == "completed"
        assert run.started_at is not None
        assert run.completed_at is not None

        report = db.query(RunReport).filter_by(run_id=run_id, section="market_report").one()
        assert report.content_markdown == "Market report body"

        metric = db.get(RunMetric, run_id)
        assert metric is not None
        assert metric.llm_calls == 2
        assert metric.tool_calls == 3

        event_types = [
            row[0]
            for row in db.execute(
                text("SELECT event_type FROM run_events WHERE run_id = :run_id ORDER BY sequence"),
                {"run_id": run_id},
            )
        ]
        assert event_types == [
            "run_created",
            "run_started",
            "agent_started",
            "report_section_streamed",
            "report_section_updated",
            "metric_updated",
            "run_completed",
        ]


def test_startup_marks_running_runs_interrupted():
    clean_db()
    run_id = create_queued_run()
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        run.status = "running"
        db.commit()

    manager = InProcessRunManager(runner=FakeRunner(), run_inline=True)
    manager.mark_running_runs_interrupted_on_startup()

    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        assert run.status == "interrupted"
        assert run.interrupted_at is not None


def test_manager_passes_web_settings_api_keys_to_runner():
    clean_db()
    run_id = create_queued_run()
    with SessionLocal() as db:
        settings = get_or_create_settings(db, "admin")
        settings.deepseek_api_key = "deepseek-db-key"
        settings.fred_api_key = "fred-db-key"
        db.commit()

    runner = RuntimeKeyCaptureRunner()
    manager = InProcessRunManager(runner=runner, run_inline=True)

    manager.start_run(run_id)

    assert runner.runtime_api_keys == {
        "DEEPSEEK_API_KEY": "deepseek-db-key",
        "FRED_API_KEY": "fred-db-key",
    }


def test_manager_falls_back_to_backend_env_api_keys_when_db_keys_are_blank(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-env-key")
    monkeypatch.setenv("FRED_API_KEY", "fred-env-key")
    run_id = create_queued_run()
    with SessionLocal() as db:
        settings = get_or_create_settings(db, "admin")
        settings.deepseek_api_key = ""
        settings.fred_api_key = ""
        db.commit()

    runner = RuntimeKeyCaptureRunner()
    manager = InProcessRunManager(runner=runner, run_inline=True)

    manager.start_run(run_id)

    assert runner.runtime_api_keys == {
        "DEEPSEEK_API_KEY": "deepseek-env-key",
        "FRED_API_KEY": "fred-env-key",
    }


def test_resume_paused_run_marks_runner_input_as_checkpoint_resume():
    clean_db()
    run_id = create_queued_run()
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        run.status = "paused"
        db.commit()

    runner = RuntimeKeyCaptureRunner()
    manager = InProcessRunManager(runner=runner, run_inline=True)

    manager.resume_run(run_id)

    assert runner.resume_from_checkpoint is True


def test_resume_paused_run_passes_prior_streamed_sections_to_runner():
    clean_db()
    run_id = create_queued_run()
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        run.status = "paused"
        db.commit()
        append_run_event(
            db,
            run_id,
            "report_section_streamed",
            {
                "section": "market_report",
                "title": "Market Analysis",
                "content_markdown": "partial body",
                "is_partial": True,
            },
            "Market Analyst",
        )
        db.commit()

    runner = RuntimeKeyCaptureRunner()
    manager = InProcessRunManager(runner=runner, run_inline=True)

    manager.resume_run(run_id)

    assert runner.resume_from_checkpoint is True
    assert runner.prior_streamed_sections == {"market_report": "partial body"}


def test_cancelled_queued_run_does_not_start_after_previous_run_finishes():
    clean_db()
    first_run_id = create_queued_run()
    second_run_id = create_queued_run()
    runner = BlockingRunner()
    manager = InProcessRunManager(runner=runner, run_inline=False, max_workers=1)

    manager.start_run(first_run_id)
    assert runner.first_run_started.wait(timeout=5)
    manager.start_run(second_run_id)
    manager.cancel_run(second_run_id)
    runner.release_first_run.set()

    future = manager._futures[first_run_id]
    future.result(timeout=5)

    with SessionLocal() as db:
        second_run = db.get(Run, second_run_id)
        assert second_run is not None
        assert second_run.status == "cancelled"
    assert runner.started_run_ids == [first_run_id]


def test_paused_queued_run_does_not_start_after_previous_run_finishes():
    clean_db()
    first_run_id = create_queued_run()
    second_run_id = create_queued_run()
    runner = BlockingRunner()
    manager = InProcessRunManager(runner=runner, run_inline=False, max_workers=1)

    manager.start_run(first_run_id)
    assert runner.first_run_started.wait(timeout=5)
    manager.start_run(second_run_id)
    manager.pause_run(second_run_id)
    runner.release_first_run.set()

    future = manager._futures[first_run_id]
    future.result(timeout=5)

    with SessionLocal() as db:
        second_run = db.get(Run, second_run_id)
        assert second_run is not None
        assert second_run.status == "paused"
    assert runner.started_run_ids == [first_run_id]


def test_running_run_pauses_and_releases_worker_for_next_run():
    clean_db()
    paused_run_id = create_queued_run()
    next_run_id = create_queued_run()
    runner = PausableRunner()
    manager = InProcessRunManager(runner=runner, run_inline=False, max_workers=1)

    manager.start_run(paused_run_id)
    assert runner.after_first_message.wait(timeout=5)
    manager.pause_run(paused_run_id)

    manager.start_run(next_run_id)
    runner.allow_second_message.set()

    wait_for_run_status(paused_run_id, "paused")
    wait_for_run_status(next_run_id, "completed")

    with SessionLocal() as db:
        paused_run = db.get(Run, paused_run_id)
        next_run = db.get(Run, next_run_id)
        assert paused_run is not None
        assert next_run is not None
        assert paused_run.status == "paused"
        assert next_run.status == "completed"


def test_running_run_waits_for_safe_point_before_pausing():
    clean_db()
    run_id = create_queued_run()
    runner = SafePointRunner()
    manager = InProcessRunManager(runner=runner, run_inline=False, max_workers=1)

    manager.start_run(run_id)
    assert runner.after_partial.wait(timeout=5)
    manager.pause_run(run_id)

    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        assert run.status == "running"

    runner.allow_completion.set()
    wait_for_run_status(run_id, "paused")

    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        assert run.status == "paused"


def test_running_run_pauses_at_agent_boundary_before_next_agent_streams():
    clean_db()
    run_id = create_queued_run()
    runner = AgentBoundaryPauseRunner()
    manager = InProcessRunManager(runner=runner, run_inline=False, max_workers=1)

    manager.start_run(run_id)
    assert runner.after_market_stream.wait(timeout=5)
    manager.pause_run(run_id)

    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        assert run.status == "running"

    runner.allow_switch.set()
    wait_for_run_status(run_id, "paused")

    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        assert run.status == "paused"
        report = db.query(RunReport).filter_by(run_id=run_id, section="market_report").one_or_none()
        assert report is not None
        assert report.content_markdown == "market body"
        events = [
            row[0]
            for row in db.execute(
                text("SELECT event_type FROM run_events WHERE run_id = :run_id ORDER BY sequence"),
                {"run_id": run_id},
            )
        ]
        assert "agent_completed" in events
        assert events.count("agent_started") == 1


def test_resume_after_market_pause_starts_sentiment_before_news():
    clean_db()
    run_id = create_queued_run()
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        run.selected_analysts = ["market", "social", "news"]
        db.commit()

    runner = ResumeOrderRunner()
    manager = InProcessRunManager(runner=runner, run_inline=True)

    manager.start_run(run_id)

    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        run.status = "paused"
        db.commit()

    manager.resume_run(run_id)

    with SessionLocal() as db:
        events = list(
            db.execute(
                text(
                    "SELECT sequence, event_type, agent_name FROM run_events "
                    "WHERE run_id = :run_id ORDER BY sequence"
                ),
                {"run_id": run_id},
            )
        )
        sentiment_started = next(
            sequence for sequence, event_type, agent_name in events
            if event_type == "agent_started" and agent_name == "Sentiment Analyst"
        )
        news_started = next(
            sequence for sequence, event_type, agent_name in events
            if event_type == "agent_started" and agent_name == "News Analyst"
        )
        assert sentiment_started < news_started
