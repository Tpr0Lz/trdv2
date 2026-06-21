from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import require_current_username
from app.schemas.auth import LoginRequest, UserResponse
from app.services.auth_service import (
    SESSION_COOKIE_NAME,
    authenticate_single_user,
    issue_session_cookie,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response) -> UserResponse:
    user = authenticate_single_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    issue_session_cookie(response, user.username)
    return user


@router.get("/me", response_model=UserResponse)
def me(username: str = Depends(require_current_username)) -> UserResponse:
    return UserResponse(id="single-user", username=username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME)
