from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AppSettingsUpdateRequest(BaseModel):
    default_llm_provider: str = Field(min_length=1, max_length=80)
    default_deep_model: str = Field(min_length=1, max_length=160)
    default_quick_model: str = Field(min_length=1, max_length=160)
    default_output_language: str = Field(min_length=1, max_length=80)
    default_analysts: list[str] = Field(min_length=1)
    default_research_depth: int = Field(ge=1, le=5)
    default_checkpoint_enabled: bool
    deepseek_api_key: str = Field(default="", max_length=512)
    fred_api_key: str = Field(default="", max_length=512)


class AppSettingsResponse(AppSettingsUpdateRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
