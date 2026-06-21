from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.db.models import RunEvent
from app.schemas.events import RunEventResponse
from app.services.sse_broker import broker


def append_run_event(
    db: Session,
    run_id: str,
    event_type: str,
    payload: dict,
    agent_name: str | None = None,
) -> RunEvent:
    """追加 run event，并按 run 内 sequence 严格递增。"""
    next_sequence = _next_sequence(db, run_id)
    event = RunEvent(
        run_id=run_id,
        event_type=event_type,
        agent_name=agent_name,
        sequence=next_sequence,
        payload=payload,
        created_at=utc_now(),
    )
    db.add(event)
    db.flush()
    broker.publish(RunEventResponse.model_validate(event))
    return event


def list_run_events(db: Session, run_id: str, after_event_id: int | None = None) -> list[RunEvent]:
    stmt: Select[tuple[RunEvent]] = select(RunEvent).where(RunEvent.run_id == run_id)
    if after_event_id is not None:
        stmt = stmt.where(RunEvent.id > after_event_id)
    stmt = stmt.order_by(RunEvent.id.asc())
    return list(db.scalars(stmt))


def _next_sequence(db: Session, run_id: str) -> int:
    current = db.scalar(select(func.max(RunEvent.sequence)).where(RunEvent.run_id == run_id))
    return int(current or 0) + 1

