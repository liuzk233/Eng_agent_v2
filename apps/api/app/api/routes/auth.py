from typing import Annotated
from time import monotonic

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.domain.auth.repository import AuthRepository
from app.domain.auth.service import AuthError, AuthService
from app.models.auth import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
_auth_attempts: dict[str, list[float]] = {}


def get_auth_service(session: Session = Depends(get_db)) -> AuthService:
    return AuthService(AuthRepository(session))


def reset_auth_rate_limiter() -> None:
    _auth_attempts.clear()


def enforce_auth_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:{request.url.path}"
    now = monotonic()
    window_start = now - settings.auth_rate_limit_window_seconds
    recent_attempts = [timestamp for timestamp in _auth_attempts.get(key, []) if timestamp >= window_start]
    if len(recent_attempts) >= settings.auth_rate_limit_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts",
        )
    recent_attempts.append(now)
    _auth_attempts[key] = recent_attempts


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = decode_access_token(authorization.removeprefix("Bearer ").strip(), settings.require_jwt_secret())
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = auth_service.get_active_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
    _: None = Depends(enforce_auth_rate_limit),
) -> TokenResponse:
    try:
        return auth_service.register(payload)
    except AuthError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    _: None = Depends(enforce_auth_rate_limit),
) -> TokenResponse:
    try:
        return auth_service.login(payload)
    except AuthError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
