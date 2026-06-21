from fastapi import Cookie, HTTPException, status

from app.services.auth_service import SESSION_COOKIE_NAME, decode_session_token


def require_current_username(
    ta_v2_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> str:
    """读取 HttpOnly session cookie，供后续 runs/settings API 复用。"""
    if ta_v2_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    username = decode_session_token(ta_v2_session)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return username

