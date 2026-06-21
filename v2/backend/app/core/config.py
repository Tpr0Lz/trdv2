from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置统一入口，避免业务代码直接读取环境变量。"""

    app_env: str = "development"
    app_secret_key: str = Field(default="change-me-in-local-env")
    database_url: str = (
        "postgresql+psycopg://tradingagents:tradingagents@localhost:54329/tradingagents_v2"
    )

    single_user_username: str = "admin"
    single_user_password: str = "admin123456"

    tradingagents_project_dir: Path = Path("../../TradingAgents")
    tradingagents_results_dir: Path = Path(".runtime/tradingagents/logs")
    tradingagents_cache_dir: Path = Path(".runtime/tradingagents/cache")
    tradingagents_memory_log_path: Path = Path(".runtime/tradingagents/memory/trading_memory.md")
    run_autostart: bool = True

    openai_api_key: str | None = None
    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    deepseek_api_key: str | None = None
    dashscope_api_key: str | None = None
    zhipu_api_key: str | None = None
    minimax_api_key: str | None = None
    openrouter_api_key: str | None = None
    alpha_vantage_api_key: str | None = None
    fred_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，测试中可通过 clear_cache 后重新读取环境。"""
    return Settings()
