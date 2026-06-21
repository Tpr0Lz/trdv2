from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.db.models import Run, RunEvidence, RunMetric, RunReport
from app.schemas.quality import RunQualityCheck, RunQualityResponse


ANALYST_REPORT_SECTIONS = {
    "market": "market_report",
    "social": "sentiment_report",
    "sentiment": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
}

CITATION_PATTERN = re.compile(r"\[E\d+\]")


def build_run_quality(db: Session, run_id: str) -> RunQualityResponse:
    run = db.get(Run, run_id)
    reports = list(db.query(RunReport).filter_by(run_id=run_id).order_by(RunReport.updated_at.asc()))
    evidence = list(db.query(RunEvidence).filter_by(run_id=run_id).order_by(RunEvidence.created_at.asc()))
    metric = db.get(RunMetric, run_id)

    checks = [
        _selected_reports_check(run, reports),
        _non_empty_reports_check(reports),
        _evidence_check(evidence),
        _citation_validity_check(reports, evidence),
        _metrics_check(metric),
        _lifecycle_check(run),
    ]
    score = max(0, 100 + sum(check.score_delta for check in checks))
    return RunQualityResponse(
        run_id=run_id,
        score=score,
        status=_quality_status(score, checks),
        checks=checks,
    )


def _selected_reports_check(run: Run | None, reports: list[RunReport]) -> RunQualityCheck:
    selected = run.selected_analysts if run is not None else []
    expected_sections = [
        ANALYST_REPORT_SECTIONS[item]
        for item in selected
        if item in ANALYST_REPORT_SECTIONS
    ]
    present_sections = {report.section for report in reports}
    missing_sections = [section for section in expected_sections if section not in present_sections]
    if missing_sections:
        return RunQualityCheck(
            id="selected_reports_present",
            title="已选报告完整性",
            status="warning",
            summary=f"缺少 {len(missing_sections)} 份已选 analyst 报告。",
            score_delta=-20,
            details={"expected_sections": expected_sections, "missing_sections": missing_sections},
        )
    return RunQualityCheck(
        id="selected_reports_present",
        title="已选报告完整性",
        status="pass",
        summary="所有已选 analyst 报告都已生成。",
        score_delta=0,
        details={"expected_sections": expected_sections, "missing_sections": []},
    )


def _non_empty_reports_check(reports: list[RunReport]) -> RunQualityCheck:
    empty_sections = [report.section for report in reports if not report.content_markdown.strip()]
    if not reports or empty_sections:
        return RunQualityCheck(
            id="reports_non_empty",
            title="报告内容非空",
            status="fail",
            summary="存在空报告内容。",
            score_delta=-25,
            details={"empty_sections": empty_sections, "report_count": len(reports)},
        )
    return RunQualityCheck(
        id="reports_non_empty",
        title="报告内容非空",
        status="pass",
        summary=f"{len(reports)} 份报告均包含内容。",
        score_delta=0,
        details={"empty_sections": [], "report_count": len(reports)},
    )


def _evidence_check(evidence: list[RunEvidence]) -> RunQualityCheck:
    if not evidence:
        return RunQualityCheck(
            id="rag_evidence_available",
            title="RAG 证据可用",
            status="warning",
            summary="本次运行尚未关联任何 RAG 证据。",
            score_delta=-10,
            details={"evidence_count": 0},
        )
    return RunQualityCheck(
        id="rag_evidence_available",
        title="RAG 证据可用",
        status="pass",
        summary=f"已关联 {len(evidence)} 条证据。",
        score_delta=0,
        details={"evidence_count": len(evidence)},
    )


def _citation_validity_check(reports: list[RunReport], evidence: list[RunEvidence]) -> RunQualityCheck:
    cited_keys = sorted({key.strip("[]") for report in reports for key in CITATION_PATTERN.findall(report.content_markdown)})
    evidence_keys = sorted({item.citation_key for item in evidence if item.citation_key})
    invalid = [key for key in cited_keys if key not in evidence_keys]
    if invalid:
        return RunQualityCheck(
            id="citation_keys_valid",
            title="引用键有效性",
            status="fail",
            summary=f"有 {len(invalid)} 个引用键无法映射到证据。",
            score_delta=-10,
            details={"cited_keys": cited_keys, "evidence_keys": evidence_keys, "invalid_citations": invalid},
        )
    if evidence and not cited_keys:
        return RunQualityCheck(
            id="citation_keys_valid",
            title="引用键有效性",
            status="warning",
            summary="已有证据，但报告尚未引用这些证据。",
            score_delta=-10,
            details={"cited_keys": cited_keys, "evidence_keys": evidence_keys, "invalid_citations": []},
        )
    return RunQualityCheck(
        id="citation_keys_valid",
        title="引用键有效性",
        status="pass",
        summary="报告中的引用均能映射到已检索证据。",
        score_delta=0,
        details={"cited_keys": cited_keys, "evidence_keys": evidence_keys, "invalid_citations": []},
    )


def _metrics_check(metric: RunMetric | None) -> RunQualityCheck:
    if metric is None or metric.llm_calls <= 0:
        return RunQualityCheck(
            id="metrics_available",
            title="指标可用性",
            status="warning",
            summary="LLM / 工具指标暂未就绪。",
            score_delta=-10,
            details={"llm_calls": 0, "tool_calls": 0},
        )
    return RunQualityCheck(
        id="metrics_available",
        title="指标可用性",
        status="pass",
        summary=f"共记录 {metric.llm_calls} 次 LLM 调用、{metric.tool_calls} 次工具调用。",
        score_delta=0,
        details={"llm_calls": metric.llm_calls, "tool_calls": metric.tool_calls},
    )


def _lifecycle_check(run: Run | None) -> RunQualityCheck:
    status = run.status if run is not None else "missing"
    if status in {"failed", "cancelled", "interrupted"}:
        return RunQualityCheck(
            id="run_lifecycle_health",
            title="运行生命周期健康度",
            status="fail",
            summary=f"运行已以{_status_label(status)}状态结束。",
            score_delta=-30,
            details={"status": status},
        )
    if status in {"queued", "running", "paused"}:
        return RunQualityCheck(
            id="run_lifecycle_health",
            title="运行生命周期健康度",
            status="warning",
            summary=f"运行当前仍处于{_status_label(status)}状态。",
            score_delta=0,
            details={"status": status},
        )
    return RunQualityCheck(
        id="run_lifecycle_health",
        title="运行生命周期健康度",
        status="pass",
        summary=f"运行状态正常，当前为{_status_label(status)}。",
        score_delta=0,
        details={"status": status},
    )


def _quality_status(score: int, checks: list[RunQualityCheck]) -> str:
    # 中文注释：单项失败不一定代表整次 run 不可用，低分或生命周期失败才整体 fail。
    if score < 50 or any(check.id == "run_lifecycle_health" and check.status == "fail" for check in checks):
        return "fail"
    if score < 100 or any(check.status != "pass" for check in checks):
        return "warning"
    return "pass"


def _status_label(status: str) -> str:
    label_by_status = {
        "completed": "已完成",
        "failed": "失败",
        "cancelled": "已取消",
        "interrupted": "中断",
        "queued": "排队中",
        "running": "运行中",
        "paused": "已暂停",
        "missing": "缺失",
    }
    return label_by_status.get(status, status)
