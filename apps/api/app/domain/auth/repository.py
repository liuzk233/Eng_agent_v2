from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_invite_code
from app.models.auth import InviteCode, User


class AuthRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_user_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def get_user_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def create_user(self, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash)
        self.session.add(user)
        self.session.flush()
        return user

    def ensure_user_with_password(self, email: str, password_hash: str) -> User:
        user = self.get_user_by_email(email)
        if user is None:
            return self.create_user(email, password_hash)
        user.password_hash = password_hash
        user.is_active = True
        self.session.add(user)
        self.session.flush()
        return user

    def get_available_invite_code(self, code: str) -> InviteCode | None:
        invite = self.session.scalar(
            select(InviteCode).where(InviteCode.code_hash == hash_invite_code(code))
        )
        if invite is None:
            return None
        if invite.used_count >= invite.max_uses:
            return None
        if invite.expires_at is not None and self._as_aware(invite.expires_at) <= datetime.now(timezone.utc):
            return None
        return invite

    def consume_invite_code(self, invite: InviteCode) -> None:
        invite.used_count += 1
        self.session.add(invite)

    @staticmethod
    def _as_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
