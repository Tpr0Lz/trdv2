from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RunReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    section: str
    title: str
    content_markdown: str
    version: int
    created_at: datetime
    updated_at: datetime


class RunReportsResponse(BaseModel):
    items: list[RunReportResponse]


class RunMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    llm_calls: int
    tool_calls: int
    tokens_in: int
    tokens_out: int
    elapsed_seconds: int
    analyst_wall_times: dict
    updated_at: datetime | None
