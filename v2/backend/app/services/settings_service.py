from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AppSettings
from app.schemas.settings import AppSettingsUpdateRequest
from app.services.run_service import ensure_single_user


DEFAULT_SETTINGS = {
    "default_llm_provider": "deepseek",
    "default_deep_model": "deepseek-v4-pro",
    "default_quick_model": "deepseek-v4-flash",
    "default_output_language": "Chinese",
    "default_analysts": ["market", "social", "news", "fundamentals"],
    "default_research_depth": 1,
    "default_checkpoint_enabled": True,
    "deepseek_api_key": "",
    "fred_api_key": "",
}

LEGACY_DEFAULTS = {
    "default_llm_provider": "openai",
    "default_deep_model": "gpt-5.5",
    "default_quick_model": "gpt-5.4-mini",
    "default_output_language": "English",
    "default_analysts": ["news"],
    "default_research_depth": 1,
    "default_checkpoint_enabled": True,
}


def get_or_create_settings(db: Session, username: str) -> AppSettings:
    """单用户系统也落库设置，创建 run 时可保存稳定配置快照。"""
    user = ensure_single_user(db, username)
    settings = db.scalar(select(AppSettings).where(AppSettings.user_id == user.id))
    if settings is not None:
        filled_from_env = fill_missing_api_keys_from_env(settings)
        if uses_legacy_defaults(settings):
            # 中文注释：旧版前端默认值会卡到 OpenAI，这里仅平滑升级完全未改过的默认组合。
            apply_default_models(settings, DEFAULT_SETTINGS)
            filled_from_env = True
        if filled_from_env:
            db.commit()
            db.refresh(settings)
        return settings

    settings = AppSettings(user_id=user.id, **DEFAULT_SETTINGS)
    fill_missing_api_keys_from_env(settings)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def update_settings(
    db: Session,
    username: str,
    payload: AppSettingsUpdateRequest,
) -> AppSettings:
    settings = get_or_create_settings(db, username)
    for key, value in payload.model_dump().items():
        if key.endswith("_api_key") and value == "":
            continue
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings


def uses_legacy_defaults(settings: AppSettings) -> bool:
    return all(getattr(settings, key) == value for key, value in LEGACY_DEFAULTS.items())


def apply_default_models(settings: AppSettings, defaults: dict[str, object]) -> None:
    for key, value in defaults.items():
        if key.endswith("_api_key"):
            continue
        setattr(settings, key, value)


def fill_missing_api_keys_from_env(settings: AppSettings) -> bool:
    backend_settings = get_settings()
    changed = False
    for field_name in ("deepseek_api_key", "fred_api_key"):
        current_value = getattr(settings, field_name, "")
        fallback_value = getattr(backend_settings, field_name, None)
        normalized_current = current_value.strip() if isinstance(current_value, str) else ""
        normalized_fallback = fallback_value.strip() if isinstance(fallback_value, str) else ""
        if normalized_current or not normalized_fallback:
            continue
        # 中文注释：数据库缺 key 时，用后端 .env 里的同名 key 补齐，避免重启后页面和运行时都读到空值。
        setattr(settings, field_name, normalized_fallback)
        changed = True
    return changed
