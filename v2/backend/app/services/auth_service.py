from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import Response

from app.core.config import get_settings
from app.schemas.auth import UserResponse

SESSION_COOKIE_NAME = "ta_v2_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 12


@dataclass(frozen=True)
class SessionPayload:
    username: str
    expires_at: int


def authenticate_single_user(username: str, password: str) -> UserResponse | None:
    """第一阶段只校验 .env 中的单用户账号，不引入复杂用户体系。"""
    settings = get_settings()
    username_ok = hmac.compare_digest(username, settings.single_user_username)
    password_ok = hmac.compare_digest(password, settings.single_user_password)
    if not username_ok or not password_ok:
        return None
    return UserResponse(id="single-user", username=settings.single_user_username)


def issue_session_cookie(response: Response, username: str) -> None:
    token = encode_session_token(
        SessionPayload(
            username=username,
            expires_at=int(time.time()) + SESSION_MAX_AGE_SECONDS,
        )
    )
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )


def encode_session_token(payload: SessionPayload) -> str:
    body = json.dumps(payload.__dict__, separators=(",", ":"), sort_keys=True).encode()
    body_b64 = _b64encode(body)
    signature = _sign(body_b64)
    return f"{body_b64}.{signature}"


def decode_session_token(token: str) -> str | None:
    try:
        body_b64, signature = token.split(".", 1)
    except ValueError:
        return None

    if not hmac.compare_digest(_sign(body_b64), signature):
        return None

    try:
        raw = base64.urlsafe_b64decode(_pad_b64(body_b64))
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None

    if int(data.get("expires_at", 0)) < int(time.time()):
        return None
    return str(data.get("username") or "")


def _sign(body_b64: str) -> str:
    digest = hmac.new(
        get_settings().app_secret_key.encode(),
        body_b64.encode(),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _pad_b64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return f"{value}{padding}".encode()

