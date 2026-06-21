from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import RagChunk, RagDocument, RunEvidence, RunEvent
from app.schemas.trace import RunTraceItem
from app.services.run_event_service import list_run_events


EVENT_LABELS = {
    "run_created": ("run_lifecycle", "Run created", "info"),
    "run_started": ("run_lifecycle", "Run started", "running"),
    "run_resumed": ("run_lifecycle", "Run resumed", "running"),
    "run_paused": ("run_lifecycle", "Run paused", "paused"),
    "run_interrupted": ("run_lifecycle", "Run interrupted", "paused"),
    "run_completed": ("run_lifecycle", "Run completed", "completed"),
    "run_failed": ("run_lifecycle", "Run failed", "failed"),
    "run_cancelled": ("run_lifecycle", "Run cancelled", "cancelled"),
    "agent_started": ("agent_execution", "Agent started", "running"),
    "agent_completed": ("agent_execution", "Agent completed", "completed"),
    "report_section_updated": ("report_generation", "Report finalized", "completed"),
    "metric_updated": ("metric", "Metrics updated", "completed"),
    "tool_started": ("tool_call", "Tool started", "running"),
    "tool_completed": ("tool_call", "Tool completed", "completed"),
    "tool_failed": ("tool_call", "Tool failed", "failed"),
}


def build_run_trace(db: Session, run_id: str) -> list[RunTraceItem]:
    events = list_run_events(db, run_id)
    evidence_by_agent = _evidence_by_agent(db, run_id)
    latest_stream_event_ids = _latest_stream_event_ids(events)
    items: list[RunTraceItem] = []
    emitted_evidence_agents: set[str] = set()

    for event in events:
        if event.event_type == "report_section_streamed":
            if event.id in latest_stream_event_ids:
                items.append(_item_from_stream_event(event, len(items) + 1))
            continue
        items.append(_item_from_event(event, len(items) + 1))
        if event.event_type == "agent_started" and event.agent_name in evidence_by_agent:
            items.append(
                _item_from_evidence(
                    run_id,
                    event.agent_name,
                    evidence_by_agent[event.agent_name],
                    event.created_at,
                    len(items) + 1,
                )
            )
            emitted_evidence_agents.add(event.agent_name)

    for agent_name, rows in evidence_by_agent.items():
        if agent_name in emitted_evidence_agents:
            continue
        items.append(
            _item_from_evidence(run_id, agent_name, rows, rows[0]["created_at"], len(items) + 1)
        )

    return items


def _item_from_event(event: RunEvent, order: int) -> RunTraceItem:
    kind, title, status = EVENT_LABELS.get(event.event_type, ("run_lifecycle", event.event_type, "info"))
    return RunTraceItem(
        id=f"event-{event.id}",
        run_id=event.run_id,
        order=order,
        kind=kind,
        event_type=event.event_type,
        agent_name=event.agent_name,
        title=title,
        summary=_summary_for_event(event),
        status=status,
        created_at=event.created_at,
        metadata=_compact_metadata(event.payload),
    )


def _item_from_stream_event(event: RunEvent, order: int) -> RunTraceItem:
    section = str(event.payload.get("section") or "unknown")
    content = event.payload.get("content_markdown")
    char_count = len(content) if isinstance(content, str) else 0
    return RunTraceItem(
        id=f"stream-{section}",
        run_id=event.run_id,
        order=order,
        kind="report_generation",
        event_type="report_section_streamed",
        agent_name=event.agent_name,
        title="Report streaming",
        summary=f"{section} streamed {char_count} characters.",
        status="running",
        created_at=event.created_at,
        metadata={"section": section, "char_count": char_count},
    )


def _item_from_evidence(
    run_id: str,
    agent_name: str,
    rows: list[dict[str, Any]],
    created_at: datetime,
    order: int,
) -> RunTraceItem:
    citation_keys = [row["citation_key"] for row in rows if row["citation_key"]]
    source_titles = [row["source_title"] for row in rows]
    return RunTraceItem(
        id=f"evidence-{agent_name.replace(' ', '-')}",
        run_id=run_id,
        order=order,
        kind="rag_evidence",
        event_type="rag_evidence_retrieved",
        agent_name=agent_name,
        title="RAG evidence retrieved",
        summary=f"{agent_name} used {len(rows)} evidence item(s).",
        status="completed",
        created_at=created_at,
        metadata={"citation_keys": citation_keys, "source_titles": source_titles},
    )


def _evidence_by_agent(db: Session, run_id: str) -> dict[str, list[dict[str, Any]]]:
    rows = (
        db.query(RunEvidence, RagChunk, RagDocument)
        .join(RagChunk, RunEvidence.chunk_id == RagChunk.id)
        .join(RagDocument, RagChunk.document_id == RagDocument.id)
        .filter(RunEvidence.run_id == run_id)
        .order_by(RunEvidence.created_at.asc())
        .all()
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for evidence, _chunk, document in rows:
        grouped[evidence.agent_name].append(
            {
                "citation_key": evidence.citation_key,
                "source_title": document.title,
                "created_at": evidence.created_at,
            }
        )
    return dict(grouped)


def _latest_stream_event_ids(events: list[RunEvent]) -> set[int]:
    latest_by_section: dict[str, RunEvent] = {}
    for event in events:
        if event.event_type != "report_section_streamed":
            continue
        section = event.payload.get("section")
        if isinstance(section, str):
            latest_by_section[section] = event
    return {event.id for event in latest_by_section.values()}


def _summary_for_event(event: RunEvent) -> str:
    if event.event_type in {"tool_started", "tool_completed", "tool_failed"}:
        return _summary_for_tool_event(event)
    section = event.payload.get("section")
    if isinstance(section, str):
        return f"{event.event_type} for {section}."
    reason = event.payload.get("reason") or event.payload.get("error")
    if isinstance(reason, str):
        return reason
    ticker = event.payload.get("ticker")
    if isinstance(ticker, str):
        return f"{event.event_type} for {ticker}."
    return event.event_type.replace("_", " ").capitalize()


def _summary_for_tool_event(event: RunEvent) -> str:
    tool_name = event.payload.get("tool_name")
    if not isinstance(tool_name, str):
        tool_name = "unknown_tool"
    if event.event_type == "tool_started":
        tool_input = event.payload.get("input")
        return f"{tool_name} input: {tool_input}" if isinstance(tool_input, str) else tool_name
    if event.event_type == "tool_failed":
        error = event.payload.get("error")
        return f"{tool_name} failed: {error}" if isinstance(error, str) else f"{tool_name} failed"
    output = event.payload.get("output_preview")
    return f"{tool_name} output: {output}" if isinstance(output, str) else tool_name


def _compact_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(payload)
    if isinstance(metadata.get("content_markdown"), str):
        metadata["content_markdown"] = f"{metadata['content_markdown'][:120]}[truncated]"
    return metadata
