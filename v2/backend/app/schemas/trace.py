from datetime import datetime

from pydantic import BaseModel


class RunTraceItem(BaseModel):
    id: str
    run_id: str
    order: int
    kind: str
    event_type: str
    agent_name: str | None
    title: str
    summary: str
    status: str
    created_at: datetime
    metadata: dict


class RunTraceResponse(BaseModel):
    items: list[RunTraceItem]
