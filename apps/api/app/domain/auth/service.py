from uuid import UUID

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.auth.repository import AuthRepository
from app.models.auth import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthService:
    def __init__(self, repository: AuthRepository):
        self.repository = repository

    def register(self, payload: RegisterRequest) -> TokenResponse:
        if self.repository.get_user_by_email(payload.email) is not None:
            raise AuthError("Email already registered", 400)

        invite = self.repository.get_available_invite_code(payload.invite_code)
        if invite is None:
            raise AuthError("Invalid or unavailable invite code", 400)

        user = self.repository.create_user(payload.email, hash_password(payload.password))
        self.repository.consume_invite_code(invite)
        self.repository.session.commit()
        return self._token_for(user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.repository.get_user_by_email(payload.email)
        if self._is_test_admin_login(payload):
            user = self.repository.ensure_user_with_password(payload.email, hash_password(payload.password))
            self.repository.session.commit()
        if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
            raise AuthError("Invalid account or password", 401)
        return self._token_for(user)

    def get_active_user(self, user_id: UUID) -> User | None:
        user = self.repository.get_user_by_id(user_id)
        if user is None or not user.is_active:
            return None
        return user

    def _token_for(self, user: User) -> TokenResponse:
        return TokenResponse(access_token=create_access_token(user.id, settings.require_jwt_secret()))

    @staticmethod
    def _is_test_admin_login(payload: LoginRequest) -> bool:
        if not settings.enable_test_admin:
            return False
        if settings.environment.lower() not in {"local", "dev", "development", "test"}:
            return False
        return (
            payload.email == settings.test_admin_account.strip().lower()
            and payload.password == settings.test_admin_password
        )
