from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.db.models import RagChunk, RagDocument, RunEvidence, RunMetric, RunReport
from app.schemas.rag import RagEvidenceItem
from app.schemas.reports import RunMetricResponse


def upsert_run_report(
    db: Session,
    run_id: str,
    section: str,
    title: str,
    content_markdown: str,
) -> RunReport:
    """按 section 保存最新报告，详情页总是读取最新版本。"""
    existing = db.query(RunReport).filter_by(run_id=run_id, section=section).one_or_none()
    if existing is None:
        report = RunReport(
            run_id=run_id,
            section=section,
            title=title,
            content_markdown=content_markdown,
            version=1,
        )
        db.add(report)
        db.flush()
        return report

    existing.title = title
    existing.content_markdown = content_markdown
    existing.version += 1
    db.flush()
    return existing


def upsert_run_metrics(db: Session, run_id: str, metrics: dict) -> None:
    """指标来自 runner 事件，使用 upsert 保持一行最新快照。"""
    values = {
        "run_id": run_id,
        "llm_calls": int(metrics.get("llm_calls", 0)),
        "tool_calls": int(metrics.get("tool_calls", 0)),
        "tokens_in": int(metrics.get("tokens_in", 0)),
        "tokens_out": int(metrics.get("tokens_out", 0)),
        "elapsed_seconds": int(metrics.get("elapsed_seconds", 0)),
        "analyst_wall_times": metrics.get("analyst_wall_times", {}),
        "updated_at": utc_now(),
    }
    stmt = insert(RunMetric).values(**values)
    update_values = {key: values[key] for key in values if key != "run_id"}
    db.execute(stmt.on_conflict_do_update(index_elements=[RunMetric.run_id], set_=update_values))


def list_run_reports(db: Session, run_id: str) -> list[RunReport]:
    """按报告更新时间展示，前端可直接渲染为 tabs。"""
    return list(db.query(RunReport).filter_by(run_id=run_id).order_by(RunReport.updated_at.asc()))


def get_run_metrics(db: Session, run_id: str) -> RunMetricResponse:
    metric = db.get(RunMetric, run_id)
    if metric is not None:
        return RunMetricResponse.model_validate(metric)
    # 中文注释：任务刚创建时可能还没有指标行，详情页仍需要稳定结构。
    return RunMetricResponse(
        run_id=run_id,
        llm_calls=0,
        tool_calls=0,
        tokens_in=0,
        tokens_out=0,
        elapsed_seconds=0,
        analyst_wall_times={},
        updated_at=None,
    )


def list_run_evidence(db: Session, run_id: str) -> list[RagEvidenceItem]:
    """读取某次 run 实际检索并注入过的 RAG 证据。"""
    rows = (
        db.query(RunEvidence, RagChunk, RagDocument)
        .join(RagChunk, RunEvidence.chunk_id == RagChunk.id)
        .join(RagDocument, RagChunk.document_id == RagDocument.id)
        .filter(RunEvidence.run_id == run_id)
        .order_by(RunEvidence.created_at.asc())
        .all()
    )
    return [
        RagEvidenceItem(
            id=evidence.id,
            run_id=evidence.run_id,
            agent_name=evidence.agent_name,
            query=evidence.query,
            citation_key=evidence.citation_key,
            score=evidence.score,
            excerpt=evidence.excerpt,
            source_id=document.source_id,
            source_title=document.title,
            source_type=document.source_type,
            source_name=document.source_name,
            published_at=document.published_at,
            url=document.url,
            created_at=evidence.created_at,
        )
        for evidence, _chunk, document in rows
    ]
