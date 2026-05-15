from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_invite_code
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.auth import InviteCode
from app.models.story import Chapter, StoryBible, StoryProject


def make_client() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Base.metadata.tables["users"],
            Base.metadata.tables["invite_codes"],
            StoryProject.__table__,
            Chapter.__table__,
            StoryBible.__table__,
        ],
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app()

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session


def seed_invite_code(testing_session: sessionmaker, code: str) -> None:
    with testing_session() as session:
        session.add(
            InviteCode(
                code_hash=hash_invite_code(code),
                max_uses=1,
                used_count=0,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        session.commit()


def register_user(client: TestClient, testing_session: sessionmaker, email: str, code: str) -> str:
    seed_invite_code(testing_session, code)
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "strong-password", "invite_code": code},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_story_project_creates_initial_chapters_and_lists_for_owner() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "student@example.com", "STORY")

    response = client.post(
        "/api/story-projects",
        headers=auth_headers(token),
        json={"title": "Mars station", "style": "science_fiction", "target_chapter_count": 3},
    )

    assert response.status_code == 201
    created = response.json()
    assert created["title"] == "Mars station"
    assert created["style"] == "science_fiction"
    assert created["target_chapter_count"] == 3
    assert created["current_chapter_number"] == 1

    listing = client.get("/api/story-projects", headers=auth_headers(token))
    assert listing.status_code == 200
    assert [project["id"] for project in listing.json()] == [created["id"]]

    with testing_session() as session:
        chapters = session.query(Chapter).order_by(Chapter.chapter_number).all()
        bible = session.query(StoryBible).one()

    assert [chapter.chapter_number for chapter in chapters] == [1, 2, 3]
    assert all(chapter.status == "draft" for chapter in chapters)
    assert bible.story_project_id.hex == created["id"].replace("-", "")


def test_exam_reading_is_forced_to_single_chapter() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "reader@example.com", "EXAM")

    response = client.post(
        "/api/story-projects",
        headers=auth_headers(token),
        json={"title": "Exam practice", "style": "exam_reading", "target_chapter_count": 9},
    )

    assert response.status_code == 201
    assert response.json()["target_chapter_count"] == 1

    with testing_session() as session:
        assert session.query(Chapter).count() == 1


def test_story_project_detail_is_scoped_to_current_user() -> None:
    client, testing_session = make_client()
    owner_token = register_user(client, testing_session, "owner@example.com", "OWNER")
    other_token = register_user(client, testing_session, "other@example.com", "OTHER")
    created = client.post(
        "/api/story-projects",
        headers=auth_headers(owner_token),
        json={"title": "Private arc", "style": "web_novel", "target_chapter_count": 2},
    ).json()

    own_detail = client.get(f"/api/story-projects/{created['id']}", headers=auth_headers(owner_token))
    other_detail = client.get(f"/api/story-projects/{created['id']}", headers=auth_headers(other_token))

    assert own_detail.status_code == 200
    assert own_detail.json()["title"] == "Private arc"
    assert other_detail.status_code == 404


def test_story_project_listing_supports_limit_and_offset() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "pager@example.com", "PAGER")
    for index in range(5):
        response = client.post(
            "/api/story-projects",
            headers=auth_headers(token),
            json={
                "title": f"Story {index}",
                "style": "science_fiction",
                "target_chapter_count": 1,
            },
        )
        assert response.status_code == 201

    full_listing = client.get("/api/story-projects", headers=auth_headers(token))
    assert full_listing.status_code == 200
    expected_titles = [project["title"] for project in full_listing.json()][1:3]

    listing = client.get(
        "/api/story-projects",
        headers=auth_headers(token),
        params={"limit": 2, "offset": 1},
    )

    assert listing.status_code == 200
    assert [project["title"] for project in listing.json()] == expected_titles


def test_story_project_listing_rejects_invalid_pagination() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "invalid-pager@example.com", "BAD-PAGER")

    response = client.get(
        "/api/story-projects",
        headers=auth_headers(token),
        params={"limit": 0, "offset": -1},
    )

    assert response.status_code == 422


def test_story_project_endpoints_require_authentication() -> None:
    client, _ = make_client()

    response = client.get("/api/story-projects")

    assert response.status_code == 401
