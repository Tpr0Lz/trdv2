from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor

from sqlalchemy import select

from app.core.config import get_settings
from app.core.run_states import RunStatus, assert_transition_allowed
from app.db.base import utc_now
from app.db.models import AppSettings, Run, RunEvent, RunReport
from app.db.session import SessionLocal
from app.services.run_artifact_service import upsert_run_metrics, upsert_run_report
from app.services.run_event_service import append_run_event
from app.services.rag_retrieval_service import build_spy_rag_contexts
from app.services.tradingagents_runner import RunExecutionInput, RunnerMessage, TradingAgentsRunner


class InProcessRunManager:
    """第一阶段使用的进程内后台任务管理器，不引入 Celery/RQ。"""

    def __init__(
        self,
        runner: object | None = None,
        run_inline: bool = False,
        max_workers: int = 1,
    ) -> None:
        self.runner = runner or TradingAgentsRunner()
        self.run_inline = run_inline
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ta-v2-run")
        self._futures: dict[str, Future] = {}
        self._pause_requests: set[str] = set()
        self._resume_requests: set[str] = set()

    def start_run(self, run_id: str) -> None:
        if self.run_inline:
            self._execute_run(run_id)
            return
        if run_id in self._futures and not self._futures[run_id].done():
            return
        self._futures[run_id] = self._executor.submit(self._execute_run, run_id)

    def resume_run(self, run_id: str) -> None:
        with SessionLocal() as db:
            run = db.get(Run, run_id)
            if run is None:
                raise ValueError("Run not found")
            if run.status == RunStatus.PAUSED.value:
                self._resume_requests.add(run_id)
                run.status = RunStatus.QUEUED.value
                run.status_reason = None
                append_run_event(db, run.id, "run_resumed", {"status": RunStatus.PAUSED.value})
                db.commit()
            elif run.status in {RunStatus.INTERRUPTED.value, RunStatus.FAILED.value}:
                self._resume_requests.add(run_id)
                append_run_event(db, run.id, "run_resumed", {"status": run.status})
                db.commit()
            else:
                raise ValueError(f"Run cannot be resumed from status {run.status}")
        self.start_run(run_id)

    def pause_run(self, run_id: str) -> None:
        future = self._futures.get(run_id)
        with SessionLocal() as db:
            run = db.get(Run, run_id)
            if run is None:
                raise ValueError("Run not found")
            if run.status == RunStatus.QUEUED.value:
                if future is not None and not future.running():
                    future.cancel()
                    self._futures.pop(run_id, None)
                run.status = RunStatus.PAUSED.value
                run.status_reason = "Paused by user"
                append_run_event(db, run.id, "run_paused", {"reason": run.status_reason})
                db.commit()
                return
            if run.status != RunStatus.RUNNING.value:
                raise ValueError(f"Run cannot be paused from status {run.status}")
            self._pause_requests.add(run_id)

    def cancel_run(self, run_id: str) -> None:
        future = self._futures.get(run_id)
        if future is not None and not future.running():
            future.cancel()
            self._futures.pop(run_id, None)
        with SessionLocal() as db:
            run = db.get(Run, run_id)
            if run is None:
                raise ValueError("Run not found")
            if run.status in {RunStatus.COMPLETED.value, RunStatus.CANCELLED.value}:
                raise ValueError(f"Run cannot be cancelled from status {run.status}")
            run.status = RunStatus.CANCELLED.value
            run.status_reason = "Cancelled by user"
            append_run_event(db, run.id, "run_cancelled", {"reason": run.status_reason})
            db.commit()

    def mark_running_runs_interrupted_on_startup(self) -> None:
        with SessionLocal() as db:
            runs = list(db.scalars(select(Run).where(Run.status == RunStatus.RUNNING.value)))
            for run in runs:
                run.status = RunStatus.INTERRUPTED.value
                run.status_reason = "Backend restarted while run was active"
                run.interrupted_at = utc_now()
                append_run_event(db, run.id, "run_interrupted", {"reason": run.status_reason})
            db.commit()

    def _execute_run(self, run_id: str) -> None:
        with SessionLocal() as db:
            run = db.get(Run, run_id)
            if run is None or run.status in {RunStatus.CANCELLED.value, RunStatus.PAUSED.value}:
                return

            if run.status in {
                RunStatus.QUEUED.value,
                RunStatus.INTERRUPTED.value,
                RunStatus.FAILED.value,
            }:
                assert_transition_allowed(RunStatus(run.status), RunStatus.RUNNING)
            run.status = RunStatus.RUNNING.value
            run.status_reason = None
            run.started_at = run.started_at or utc_now()
            append_run_event(db, run.id, "run_started", {"ticker": run.ticker})
            db.commit()

            rag_contexts = build_spy_rag_contexts(db, run.id, run.ticker)
            db.commit()

            run_input = RunExecutionInput(
                run_id=run.id,
                ticker=run.ticker,
                analysis_date=run.analysis_date.isoformat(),
                asset_type=run.asset_type,
                selected_analysts=run.selected_analysts,
                config_snapshot=run.config_snapshot,
                checkpoint_thread_id=run.checkpoint_thread_id,
                runtime_api_keys=self._runtime_api_keys(db, run.user_id),
                resume_from_checkpoint=run_id in self._resume_requests,
                prior_streamed_sections=self._load_prior_streamed_sections(db, run_id),
                rag_contexts=rag_contexts,
            )

            try:
                for message in self.runner.run(run_input):
                    run = db.get(Run, run_id)
                    if run is None or run.status == RunStatus.CANCELLED.value:
                        return
                    self._persist_runner_message(db, run.id, message)
                    db.commit()
                    if run_id in self._pause_requests and self._is_pause_safe_point(message):
                        run = db.get(Run, run_id)
                        if run is not None:
                            run.status = RunStatus.PAUSED.value
                            run.status_reason = "Paused by user"
                            append_run_event(db, run.id, "run_paused", {"reason": run.status_reason})
                            db.commit()
                        self._pause_requests.discard(run_id)
                        return

                run = db.get(Run, run_id)
                if run is None or run.status == RunStatus.CANCELLED.value:
                    return
                run.status = RunStatus.COMPLETED.value
                run.completed_at = utc_now()
                append_run_event(db, run.id, "run_completed", {"ticker": run.ticker})
                db.commit()
            except Exception as exc:
                db.rollback()
                run = db.get(Run, run_id)
                if run is not None:
                    run.status = RunStatus.FAILED.value
                    run.status_reason = str(exc)
                    run.failed_at = utc_now()
                    append_run_event(db, run.id, "run_failed", {"error": str(exc)})
                    db.commit()
                raise
            finally:
                self._pause_requests.discard(run_id)
                self._resume_requests.discard(run_id)
                future = self._futures.get(run_id)
                if future is not None and future.done():
                    self._futures.pop(run_id, None)

    def _is_pause_safe_point(self, message: RunnerMessage) -> bool:
        # 中文注释：当前 agent 完成后就允许暂停，避免把暂停拖到下一个 team。
        return message.event_type in {"agent_completed", "report_section_updated", "metric_updated"}

    def _load_prior_streamed_sections(self, db, run_id: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        for event in db.scalars(
            select(RunEvent).where(
                RunEvent.run_id == run_id,
                RunEvent.event_type == "report_section_streamed",
            ).order_by(RunEvent.id.asc())
        ):
            section = event.payload.get("section")
            content = event.payload.get("content_markdown")
            if isinstance(section, str) and isinstance(content, str):
                sections[section] = content
        for report in db.scalars(
            select(RunReport).where(RunReport.run_id == run_id).order_by(RunReport.updated_at.asc())
        ):
            sections[report.section] = report.content_markdown
        return sections

    def _persist_runner_message(self, db, run_id: str, message: RunnerMessage) -> None:
        append_run_event(db, run_id, message.event_type, message.payload, message.agent_name)
        if (
            message.event_type in {"report_section_updated", "agent_completed"}
            and message.report_section
            and message.report_title
        ):
            report_markdown = message.report_markdown
            if report_markdown is None and message.event_type == "agent_completed":
                report_markdown = self._load_prior_streamed_sections(db, run_id).get(message.report_section)
            if report_markdown is None:
                report_markdown = None
            if report_markdown is None:
                return
            upsert_run_report(
                db,
                run_id,
                message.report_section,
                message.report_title,
                report_markdown,
            )
        if message.metrics is not None:
            upsert_run_metrics(db, run_id, message.metrics)

    def _runtime_api_keys(self, db, user_id: str) -> dict[str, str]:
        backend_settings = get_settings()
        settings = db.scalar(select(AppSettings).where(AppSettings.user_id == user_id))
        if settings is None:
            return {
                "DEEPSEEK_API_KEY": backend_settings.deepseek_api_key or "",
                "FRED_API_KEY": backend_settings.fred_api_key or "",
            }
        # 中文注释：运行时只注入网页配置的 key，不把 key 写入 run 快照。
        return {
            "DEEPSEEK_API_KEY": settings.deepseek_api_key or backend_settings.deepseek_api_key or "",
            "FRED_API_KEY": settings.fred_api_key or backend_settings.fred_api_key or "",
        }
