from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RunEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str
    event_type: str
    agent_name: str | None
    sequence: int
    payload: dict
    created_at: datetime


class RunEventsResponse(BaseModel):
    items: list[RunEventResponse]

