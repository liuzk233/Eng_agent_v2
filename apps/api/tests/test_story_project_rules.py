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
from app.models.generation import GenerationTask, QualityReport
from app.models.progress import LearningProgress
from app.models.story import Chapter, ChapterState, StoryBible, StoryProject
from app.models.vocabulary import ChapterTargetWord


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
            ChapterState.__table__,
            StoryBible.__table__,
            GenerationTask.__table__,
            QualityReport.__table__,
            ChapterTargetWord.__table__,
            LearningProgress.__table__,
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
    assert "3 chapter(s)" in bible.main_plot
    assert len(bible.immutable_facts["chapter_outline"]) == 3
    assert "Chapter 3" in bible.immutable_facts["chapter_outline"][-1]


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


def test_rename_story_project_updates_title_for_owner() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "renamer@example.com", "RENAME")
    created = client.post(
        "/api/story-projects",
        headers=auth_headers(token),
        json={"title": "Original title", "style": "science_fiction", "target_chapter_count": 2},
    ).json()

    response = client.patch(
        f"/api/story-projects/{created['id']}",
        headers=auth_headers(token),
        json={"title": "  Custom study arc  "},
    )

    assert response.status_code == 200
    renamed = response.json()
    assert renamed["id"] == created["id"]
    assert renamed["title"] == "Custom study arc"

    detail = client.get(f"/api/story-projects/{created['id']}", headers=auth_headers(token))
    assert detail.status_code == 200
    assert detail.json()["title"] == "Custom study arc"

    with testing_session() as session:
        bible = session.query(StoryBible).one()
        chapters = session.query(Chapter).order_by(Chapter.chapter_number).all()

    assert "Original title" in bible.main_plot
    assert "Custom study arc" not in bible.main_plot
    assert [chapter.chapter_number for chapter in chapters] == [1, 2]


def test_rename_story_project_rejects_blank_title() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "blank-renamer@example.com", "BLANK-RENAME")
    created = client.post(
        "/api/story-projects",
        headers=auth_headers(token),
        json={"title": "Keep me", "style": "web_novel", "target_chapter_count": 1},
    ).json()

    response = client.patch(
        f"/api/story-projects/{created['id']}",
        headers=auth_headers(token),
        json={"title": "   "},
    )

    assert response.status_code == 422

    detail = client.get(f"/api/story-projects/{created['id']}", headers=auth_headers(token))
    assert detail.status_code == 200
    assert detail.json()["title"] == "Keep me"


def test_rename_story_project_accepts_trimmed_title_at_max_length() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "max-renamer@example.com", "MAX-RENAME")
    created = client.post(
        "/api/story-projects",
        headers=auth_headers(token),
        json={"title": "Boundary title", "style": "web_novel", "target_chapter_count": 1},
    ).json()
    title = "A" * 160

    response = client.patch(
        f"/api/story-projects/{created['id']}",
        headers=auth_headers(token),
        json={"title": f"  {title}  "},
    )

    assert response.status_code == 200
    assert response.json()["title"] == title

    detail = client.get(f"/api/story-projects/{created['id']}", headers=auth_headers(token))
    assert detail.status_code == 200
    assert detail.json()["title"] == title


def test_rename_story_project_rejects_trimmed_title_over_max_length() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "over-max-renamer@example.com", "OVERMAX-RENAME")
    created = client.post(
        "/api/story-projects",
        headers=auth_headers(token),
        json={"title": "Keep boundary", "style": "web_novel", "target_chapter_count": 1},
    ).json()

    response = client.patch(
        f"/api/story-projects/{created['id']}",
        headers=auth_headers(token),
        json={"title": f"  {'A' * 161}  "},
    )

    assert response.status_code == 422

    detail = client.get(f"/api/story-projects/{created['id']}", headers=auth_headers(token))
    assert detail.status_code == 200
    assert detail.json()["title"] == "Keep boundary"


def test_rename_story_project_is_scoped_to_current_user() -> None:
    client, testing_session = make_client()
    owner_token = register_user(client, testing_session, "rename-owner@example.com", "RENAME-OWNER")
    other_token = register_user(client, testing_session, "rename-other@example.com", "RENAME-OTHER")
    created = client.post(
        "/api/story-projects",
        headers=auth_headers(owner_token),
        json={"title": "Owner title", "style": "science_fiction", "target_chapter_count": 1},
    ).json()

    response = client.patch(
        f"/api/story-projects/{created['id']}",
        headers=auth_headers(other_token),
        json={"title": "Stolen title"},
    )

    assert response.status_code == 404

    detail = client.get(f"/api/story-projects/{created['id']}", headers=auth_headers(owner_token))
    assert detail.status_code == 200
    assert detail.json()["title"] == "Owner title"


def test_delete_story_project_removes_owner_story_and_dependents() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "delete-owner@example.com", "DELETE-OWNER")
    created = client.post(
        "/api/story-projects",
        headers=auth_headers(token),
        json={"title": "Delete me", "style": "science_fiction", "target_chapter_count": 2},
    ).json()

    with testing_session() as session:
        project = session.query(StoryProject).filter_by(title="Delete me").one()
        chapter = (
            session.query(Chapter)
            .filter_by(story_project_id=project.id, chapter_number=1)
            .one()
        )
        task = GenerationTask(chapter_id=chapter.id, status="completed")
        session.add_all(
            [
                ChapterState(chapter_id=chapter.id, summary="A short memory"),
                ChapterTargetWord(
                    chapter_id=chapter.id,
                    word="Adventure",
                    lemma="adventure",
                    source="manual",
                    position=1,
                ),
                task,
                LearningProgress(
                    user_id=project.user_id,
                    lemma="adventure",
                    encounter_count=1,
                    last_seen_chapter_id=chapter.id,
                ),
            ]
        )
        session.flush()
        session.add(
            QualityReport(
                generation_task_id=task.id,
                chapter_id=chapter.id,
                passed=True,
            )
        )
        session.commit()

    response = client.delete(f"/api/story-projects/{created['id']}", headers=auth_headers(token))

    assert response.status_code == 204
    assert response.content == b""
    listing = client.get("/api/story-projects", headers=auth_headers(token))
    assert listing.status_code == 200
    assert [project["id"] for project in listing.json()] == []

    with testing_session() as session:
        assert session.query(StoryProject).count() == 0
        assert session.query(Chapter).count() == 0
        assert session.query(ChapterState).count() == 0
        assert session.query(ChapterTargetWord).count() == 0
        assert session.query(StoryBible).count() == 0
        assert session.query(GenerationTask).count() == 0
        assert session.query(QualityReport).count() == 0
        progress = session.query(LearningProgress).one()

    assert progress.last_seen_chapter_id is None


def test_delete_story_project_returns_404_for_missing_story() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "missing-delete@example.com", "MISSING-DELETE")

    response = client.delete(
        "/api/story-projects/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Story project not found"


def test_delete_story_project_is_scoped_to_current_user() -> None:
    client, testing_session = make_client()
    owner_token = register_user(client, testing_session, "delete-scope-owner@example.com", "DELETE-SCOPE-OWNER")
    other_token = register_user(client, testing_session, "delete-scope-other@example.com", "DELETE-SCOPE-OTHER")
    created = client.post(
        "/api/story-projects",
        headers=auth_headers(owner_token),
        json={"title": "Owner story", "style": "web_novel", "target_chapter_count": 1},
    ).json()

    response = client.delete(
        f"/api/story-projects/{created['id']}",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Story project not found"

    detail = client.get(f"/api/story-projects/{created['id']}", headers=auth_headers(owner_token))
    assert detail.status_code == 200
    assert detail.json()["title"] == "Owner story"


def test_chapter_listing_returns_all_chapter_statuses_for_owner() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "chapter-list@example.com", "CHAPTER-LIST")
    created = client.post(
        "/api/story-projects",
        headers=auth_headers(token),
        json={"title": "Directory arc", "style": "science_fiction", "target_chapter_count": 3},
    ).json()

    response = client.get(
        f"/api/story-projects/{created['id']}/chapters",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    chapters = response.json()
    assert [chapter["chapter_number"] for chapter in chapters] == [1, 2, 3]
    assert [chapter["status"] for chapter in chapters] == ["draft", "draft", "draft"]
    assert all(chapter["has_output"] is False for chapter in chapters)
    assert all(chapter["latest_generation_task"] is None for chapter in chapters)


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
