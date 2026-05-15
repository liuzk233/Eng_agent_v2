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
from app.models.vocabulary import ChapterTargetWord, ExamSyllabus, SyllabusWord


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
            ExamSyllabus.__table__,
            SyllabusWord.__table__,
            ChapterTargetWord.__table__,
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


def create_story(client: TestClient, token: str) -> dict:
    response = client.post(
        "/api/story-projects",
        headers=auth_headers(token),
        json={"title": "Mars station", "style": "science_fiction", "target_chapter_count": 2},
    )
    assert response.status_code == 201
    return response.json()


def seed_syllabus(testing_session: sessionmaker) -> None:
    with testing_session() as session:
        syllabus = ExamSyllabus(
            code="gaokao",
            name="Gaokao English",
            version="2026",
            source_description="test fixture",
            is_active=True,
        )
        session.add(syllabus)
        session.flush()
        session.add_all(
            [
                SyllabusWord(
                    syllabus_id=syllabus.id,
                    lemma="achieve",
                    allowed_forms=["achieves", "achieved", "achieving"],
                    part_of_speech="verb",
                    definition_cn="实现",
                ),
                SyllabusWord(
                    syllabus_id=syllabus.id,
                    lemma="analysis",
                    allowed_forms=["analyses"],
                    part_of_speech="noun",
                    definition_cn="分析",
                ),
            ]
        )
        session.commit()


def test_query_active_gaokao_vocabulary_by_lemma_prefix() -> None:
    client, testing_session = make_client()
    seed_syllabus(testing_session)
    token = register_user(client, testing_session, "vocab@example.com", "VOCAB")

    unauthenticated = client.get("/api/vocabularies", params={"query": "achi"})
    assert unauthenticated.status_code == 401

    response = client.get(
        "/api/vocabularies",
        headers=auth_headers(token),
        params={"query": "achi"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "lemma": "achieve",
            "allowed_forms": ["achieves", "achieved", "achieving"],
            "part_of_speech": "verb",
            "definition_cn": "实现",
        }
    ]


def test_submit_target_words_merges_manual_and_library_sources() -> None:
    client, testing_session = make_client()
    seed_syllabus(testing_session)
    token = register_user(client, testing_session, "student@example.com", "WORDS")
    story = create_story(client, token)

    response = client.post(
        f"/api/story-projects/{story['id']}/chapters/1/words",
        headers=auth_headers(token),
        json={
            "words": [
                {"word": "Achieved", "lemma": "achieve", "source": "manual"},
                {"word": "achieve", "source": "library"},
                {"word": "analysis", "source": "library"},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["words"] == [
        {"word": "Achieved", "lemma": "achieve", "source": "manual", "position": 1},
        {"word": "analysis", "lemma": "analysis", "source": "library", "position": 2},
    ]

    with testing_session() as session:
        stored = session.query(ChapterTargetWord).order_by(ChapterTargetWord.position).all()

    assert [(word.lemma, word.source, word.position) for word in stored] == [
        ("achieve", "manual", 1),
        ("analysis", "library", 2),
    ]


def test_submit_target_words_rejects_more_than_ten_words_at_api_boundary() -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "limit@example.com", "LIMIT")
    story = create_story(client, token)

    response = client.post(
        f"/api/story-projects/{story['id']}/chapters/1/words",
        headers=auth_headers(token),
        json={
            "words": [
                {"word": f"word-{index}", "source": "manual"}
                for index in range(11)
            ]
        },
    )

    assert response.status_code == 422


def test_submit_target_words_is_scoped_to_story_owner() -> None:
    client, testing_session = make_client()
    owner_token = register_user(client, testing_session, "owner@example.com", "OWNER-WORDS")
    other_token = register_user(client, testing_session, "other@example.com", "OTHER-WORDS")
    story = create_story(client, owner_token)

    response = client.post(
        f"/api/story-projects/{story['id']}/chapters/1/words",
        headers=auth_headers(other_token),
        json={"words": [{"word": "achieve", "source": "manual"}]},
    )

    assert response.status_code == 404
