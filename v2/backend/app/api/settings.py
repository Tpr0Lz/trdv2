from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_current_username
from app.db.session import get_db
from app.schemas.settings import AppSettingsResponse, AppSettingsUpdateRequest
from app.services import settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=AppSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> AppSettingsResponse:
    return settings_service.get_or_create_settings(db, username)


@router.put("", response_model=AppSettingsResponse)
def update_settings(
    payload: AppSettingsUpdateRequest,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> AppSettingsResponse:
    return settings_service.update_settings(db, username, payload)
