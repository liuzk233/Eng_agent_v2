from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_invite_code
from app.db.base import Base
from app.db.session import get_db
from app.domain.generation.repository import GenerationRepository
from app.main import create_app
from app.models.auth import InviteCode, User
from app.models.generation import GenerationTask
from app.models.story import Chapter, StoryProject
from app.models.vocabulary import ChapterTargetWord, ExamSyllabus, SyllabusWord

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.data.import_kaoyan_syllabus import DEFAULT_SOURCE_PATH, import_kaoyan_syllabus, load_snapshot


def make_client() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app()

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session


def register_user(client: TestClient, testing_session: sessionmaker) -> str:
    code = "KAOYAN"
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

    response = client.post(
        "/api/auth/register",
        json={"email": "kaoyan@example.com", "password": "strong-password", "invite_code": code},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_import_kaoyan_syllabus_is_active_and_idempotent() -> None:
    _, testing_session = make_client()
    expected_count = load_snapshot(DEFAULT_SOURCE_PATH)["word_count"]
    assert expected_count == 5491

    with testing_session() as session:
        old_syllabus = ExamSyllabus(code="gaokao", name="Gaokao English", version="2026", is_active=True)
        session.add(old_syllabus)
        session.flush()
        session.add(SyllabusWord(syllabus_id=old_syllabus.id, lemma="legacy", allowed_forms=[]))

        first_syllabus, first_count = import_kaoyan_syllabus(session)
        session.commit()
        first_syllabus_id = first_syllabus.id

        second_syllabus, second_count = import_kaoyan_syllabus(session)
        session.commit()

        active_syllabi = list(session.scalars(select(ExamSyllabus).where(ExamSyllabus.is_active.is_(True))))
        word_count = session.scalar(
            select(func.count()).select_from(SyllabusWord).where(SyllabusWord.syllabus_id == first_syllabus_id)
        )
        abandon_count = session.scalar(
            select(func.count()).select_from(SyllabusWord).where(SyllabusWord.lemma == "abandon")
        )

    assert first_count == expected_count
    assert second_count == expected_count
    assert second_syllabus.id == first_syllabus_id
    assert [(syllabus.code, syllabus.version) for syllabus in active_syllabi] == [("kaoyan", "1.0")]
    assert word_count == expected_count
    assert abandon_count == 1


def test_imported_kaoyan_words_are_visible_to_api_and_generation_state() -> None:
    client, testing_session = make_client()
    with testing_session() as session:
        import_kaoyan_syllabus(session)
        user = User(email="state@example.com", password_hash="hash", is_active=True)
        session.add(user)
        session.flush()
        project = StoryProject(
            user_id=user.id,
            title="Exam prep",
            style="web_novel",
            target_chapter_count=1,
            current_chapter_number=1,
        )
        session.add(project)
        session.flush()
        chapter = Chapter(story_project_id=project.id, chapter_number=1, status="draft")
        session.add(chapter)
        session.flush()
        task = GenerationTask(chapter_id=chapter.id)
        session.add(task)
        session.add(ChapterTargetWord(chapter_id=chapter.id, word="Abandon", lemma="abandon", source="manual", position=1))
        session.commit()

        state = GenerationRepository(session).build_generation_state(task)

    token = register_user(client, testing_session)
    response = client.get(
        "/api/vocabularies",
        headers={"Authorization": f"Bearer {token}"},
        params={"query": "abandon"},
    )

    assert response.status_code == 200
    assert response.json()[0] == {
        "lemma": "abandon",
        "allowed_forms": [],
        "part_of_speech": None,
        "definition_cn": None,
    }
    assert "abandon" in state.syllabus_lemmas
