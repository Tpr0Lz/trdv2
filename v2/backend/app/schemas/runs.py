from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class RunCreateRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=40)
    analysis_date: date
    asset_type: str = Field(default="stock", min_length=1, max_length=40)
    selected_analysts: list[str] = Field(min_length=1)
    research_depth: int = Field(ge=1, le=5)
    llm_provider: str = Field(min_length=1)
    deep_think_llm: str = Field(min_length=1)
    quick_think_llm: str = Field(min_length=1)
    output_language: str = Field(default="English", min_length=1)


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticker: str
    analysis_date: date
    asset_type: str
    status: str
    status_reason: str | None
    selected_analysts: list[str]
    config_snapshot: dict
    checkpoint_thread_id: str
    started_at: datetime | None
    completed_at: datetime | None
    interrupted_at: datetime | None
    failed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RunListResponse(BaseModel):
    items: list[RunResponse]
