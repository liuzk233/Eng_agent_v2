from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_invite_code, hash_password, verify_password
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.auth import InviteCode, User
from app.api.routes.auth import reset_auth_rate_limiter


def make_client() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[User.__table__, InviteCode.__table__])
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app()

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session


def seed_invite_code(testing_session: sessionmaker, code: str, max_uses: int = 1) -> None:
    with testing_session() as session:
        session.add(
            InviteCode(
                code_hash=hash_invite_code(code),
                max_uses=max_uses,
                used_count=0,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        session.commit()


def test_register_requires_valid_invite_code_and_stores_hashed_password() -> None:
    client, testing_session = make_client()

    response = client.post(
        "/api/auth/register",
        json={
            "email": "Student@Example.com",
            "password": "strong-password",
            "invite_code": "missing-code",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or unavailable invite code"

    seed_invite_code(testing_session, "INVITE-2026")
    response = client.post(
        "/api/auth/register",
        json={
            "email": "Student@Example.com",
            "password": "strong-password",
            "invite_code": "INVITE-2026",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]

    with testing_session() as session:
        user = session.query(User).filter_by(email="student@example.com").one()
        invite = session.query(InviteCode).one()

    assert user.password_hash != "strong-password"
    assert user.password_hash.startswith("pbkdf2_sha256$")
    assert invite.used_count == 1


def test_invite_code_cannot_be_reused_past_max_uses() -> None:
    client, testing_session = make_client()
    seed_invite_code(testing_session, "ONCE")

    first = client.post(
        "/api/auth/register",
        json={"email": "first@example.com", "password": "strong-password", "invite_code": "ONCE"},
    )
    second = client.post(
        "/api/auth/register",
        json={"email": "second@example.com", "password": "strong-password", "invite_code": "ONCE"},
    )

    assert first.status_code == 201
    assert second.status_code == 400
    assert second.json()["detail"] == "Invalid or unavailable invite code"


def test_login_and_me_use_jwt_bearer_session() -> None:
    client, testing_session = make_client()
    seed_invite_code(testing_session, "LOGIN")
    client.post(
        "/api/auth/register",
        json={"email": "student@example.com", "password": "strong-password", "invite_code": "LOGIN"},
    )

    bad_login = client.post(
        "/api/auth/login",
        json={"email": "student@example.com", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401

    login = client.post(
        "/api/auth/login",
        json={"email": "student@example.com", "password": "strong-password"},
    )
    assert login.status_code == 200

    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me.status_code == 200
    assert me.json()["email"] == "student@example.com"


def test_test_admin_account_is_disabled_by_default() -> None:
    client, testing_session = make_client()

    login = client.post(
        "/api/auth/login",
        json={"email": "admin138", "password": "0507138"},
    )
    assert login.status_code == 401

    with testing_session() as session:
        assert session.query(User).filter_by(email="admin138").one_or_none() is None


def test_test_admin_account_requires_explicit_feature_flag() -> None:
    settings.enable_test_admin = True
    settings.test_admin_account = "admin138"
    settings.test_admin_password = "0507138"
    client, testing_session = make_client()

    login = client.post(
        "/api/auth/login",
        json={"email": "admin138", "password": "0507138"},
    )
    assert login.status_code == 200

    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me.status_code == 200
    assert me.json()["email"] == "admin138"

    with testing_session() as session:
        user = session.query(User).filter_by(email="admin138").one()
    assert user.is_active is True
    assert user.password_hash != "0507138"


def test_test_admin_account_rejects_wrong_password() -> None:
    settings.enable_test_admin = True
    settings.test_admin_account = "admin138"
    settings.test_admin_password = "0507138"
    client, testing_session = make_client()

    login = client.post(
        "/api/auth/login",
        json={"email": "admin138", "password": "wrong"},
    )

    assert login.status_code == 401
    with testing_session() as session:
        assert session.query(User).filter_by(email="admin138").one_or_none() is None


def test_test_admin_account_refreshes_existing_credentials() -> None:
    settings.enable_test_admin = True
    settings.test_admin_account = "admin138"
    settings.test_admin_password = "0507138"
    client, testing_session = make_client()
    with testing_session() as session:
        session.add(User(email="admin138", password_hash=hash_password("old-password"), is_active=False))
        session.commit()

    login = client.post(
        "/api/auth/login",
        json={"email": "admin138", "password": "0507138"},
    )

    assert login.status_code == 200
    with testing_session() as session:
        user = session.query(User).filter_by(email="admin138").one()
    assert user.is_active is True
    assert verify_password("0507138", user.password_hash)


def test_me_rejects_missing_or_invalid_token() -> None:
    client, _ = make_client()

    missing = client.get("/api/auth/me")
    invalid = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})

    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_login_rate_limit_blocks_repeated_attempts() -> None:
    reset_auth_rate_limiter()
    settings.auth_rate_limit_max_attempts = 2
    settings.auth_rate_limit_window_seconds = 60
    client, _ = make_client()

    first = client.post("/api/auth/login", json={"email": "student@example.com", "password": "wrong"})
    second = client.post("/api/auth/login", json={"email": "student@example.com", "password": "wrong"})
    third = client.post("/api/auth/login", json={"email": "student@example.com", "password": "wrong"})

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    assert third.json()["detail"] == "Too many authentication attempts"
