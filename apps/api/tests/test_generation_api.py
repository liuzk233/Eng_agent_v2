from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_invite_code
from app.db.base import Base
from app.db.session import get_db
from app.domain.enums import GenerationStatus
from app.domain.generation.graphs.chapter_generation import GenerationState
from app.domain.generation.repository import GenerationRepository
from app.domain.generation.service import GenerationService
from app.domain.review.base import QualityReviewResult
from app.integrations.llm.base import ChapterGenerationOutput
from app.main import create_app
from app.models.auth import InviteCode
from app.models.generation import GenerationTask, QualityReport
from app.models.story import Chapter, ChapterState, StoryProject
from app.models.vocabulary import ChapterTargetWord, ExamSyllabus, SyllabusWord


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


def submit_words(client: TestClient, token: str, story_id: str) -> None:
    response = client.post(
        f"/api/story-projects/{story_id}/chapters/1/words",
        headers=auth_headers(token),
        json={"words": [{"word": "Adventure", "lemma": "adventure", "source": "manual"}]},
    )
    assert response.status_code == 200


def seed_syllabus(testing_session: sessionmaker) -> None:
    with testing_session() as session:
        syllabus = ExamSyllabus(
            code="gaokao",
            name="Gaokao English",
            version="2026",
            is_active=True,
        )
        session.add(syllabus)
        session.flush()
        session.add_all(
            [
                SyllabusWord(
                    syllabus_id=syllabus.id,
                    lemma="adventure",
                    allowed_forms=["adventures"],
                    definition_cn="冒险",
                ),
                SyllabusWord(
                    syllabus_id=syllabus.id,
                    lemma="student",
                    allowed_forms=["students"],
                    definition_cn="学生",
                ),
            ]
        )
        session.commit()


def test_generate_chapter_creates_persistent_task_and_enqueues_state(monkeypatch) -> None:
    client, testing_session = make_client()
    seed_syllabus(testing_session)
    token = register_user(client, testing_session, "generation@example.com", "GEN")
    story = create_story(client, token)
    submit_words(client, token, story["id"])
    captured_states: list[GenerationState] = []

    def fake_enqueue(self: GenerationService, state: GenerationState) -> str:
        captured_states.append(state)
        return "celery-task-id"

    monkeypatch.setattr(GenerationService, "enqueue", fake_enqueue)

    response = client.post(
        f"/api/story-projects/{story['id']}/chapters/1/generate",
        headers=auth_headers(token),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["retry_count"] == 0
    assert captured_states[0].target_words == ["adventure"]
    assert captured_states[0].syllabus_lemmas >= {"adventure", "student"}

    with testing_session() as session:
        task = session.scalar(select(GenerationTask))
        chapter = session.scalar(select(Chapter).where(Chapter.story_project_id == UUID(story["id"])))

    assert task is not None
    assert str(task.id) == body["id"]
    assert chapter.status == GenerationStatus.queued


def test_generate_chapter_rejects_missing_target_words(monkeypatch) -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "empty@example.com", "EMPTY")
    story = create_story(client, token)
    monkeypatch.setattr(GenerationService, "enqueue", lambda self, state: "not-called")

    response = client.post(
        f"/api/story-projects/{story['id']}/chapters/1/generate",
        headers=auth_headers(token),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Target words are required before generation"


def test_generation_task_is_scoped_to_story_owner(monkeypatch) -> None:
    client, testing_session = make_client()
    owner_token = register_user(client, testing_session, "owner-generation@example.com", "OWNER-GEN")
    other_token = register_user(client, testing_session, "other-generation@example.com", "OTHER-GEN")
    story = create_story(client, owner_token)
    submit_words(client, owner_token, story["id"])
    monkeypatch.setattr(GenerationService, "enqueue", lambda self, state: "celery-task-id")

    created = client.post(
        f"/api/story-projects/{story['id']}/chapters/1/generate",
        headers=auth_headers(owner_token),
    ).json()

    owner_response = client.get(
        f"/api/generation-tasks/{created['id']}",
        headers=auth_headers(owner_token),
    )
    other_response = client.get(
        f"/api/generation-tasks/{created['id']}",
        headers=auth_headers(other_token),
    )

    assert owner_response.status_code == 200
    assert other_response.status_code == 404


def test_chapter_listing_exposes_latest_generation_task_for_resume(monkeypatch) -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "resume-generation@example.com", "RESUME-GEN")
    story = create_story(client, token)
    submit_words(client, token, story["id"])
    monkeypatch.setattr(GenerationService, "enqueue", lambda self, state: "celery-task-id")

    created = client.post(
        f"/api/story-projects/{story['id']}/chapters/1/generate",
        headers=auth_headers(token),
    ).json()

    response = client.get(
        f"/api/story-projects/{story['id']}/chapters",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    first_chapter = response.json()[0]
    assert first_chapter["status"] == "queued"
    assert first_chapter["target_words"] == [
        {"word": "Adventure", "lemma": "adventure", "source": "manual", "position": 1}
    ]
    assert first_chapter["latest_generation_task"]["id"] == created["id"]
    assert first_chapter["latest_generation_task"]["status"] == "queued"


def test_completed_generation_persists_chapter_output_for_api_read(monkeypatch) -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "chapter-output@example.com", "OUTPUT")
    story = create_story(client, token)
    submit_words(client, token, story["id"])
    monkeypatch.setattr(GenerationService, "enqueue", lambda self, state: "celery-task-id")

    task_body = client.post(
        f"/api/story-projects/{story['id']}/chapters/1/generate",
        headers=auth_headers(token),
    ).json()

    with testing_session() as session:
        task = session.get(GenerationTask, UUID(task_body["id"]))
        quality = QualityReviewResult(
            word_count=300,
            target_word_hits={"adventure": 1},
            out_of_syllabus_rate=0,
            passed=True,
        )
        state = GenerationState(
            generation_task_id=str(task.id),
            project_id=story["id"],
            chapter_id=str(task.chapter_id),
            final_status=GenerationStatus.completed,
            retry_count=0,
            draft_output=ChapterGenerationOutput(
                english_content="The **adventure** helped every student learn.",
                highlighted_target_words=["adventure"],
                chinese_translation="这次冒险帮助每个学生学习。",
            ),
            quality_result=quality,
        )
        repository = GenerationRepository(session)
        repository.complete_generation_task(state)
        session.commit()

    response = client.get(
        f"/api/story-projects/{story['id']}/chapters/1",
        headers=auth_headers(token),
    )
    result_response = client.get(
        f"/api/story-projects/{story['id']}/chapters/1/generation-result",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["output"]["english_content"].startswith("The **adventure**")
    assert result_response.status_code == 200
    result_body = result_response.json()
    assert result_body["task"]["id"] == task_body["id"]
    assert result_body["output"]["highlighted_target_words"] == ["adventure"]
    assert result_body["quality_report"]["chapter_id"] == body["id"]
    assert result_body["quality_report"]["target_word_hits"] == {"adventure": 1}
    assert result_body["quality_report"]["passed"] is True

    with testing_session() as session:
        report = session.scalar(select(QualityReport))
        project = session.get(StoryProject, UUID(story["id"]))

    assert report is not None
    assert report.target_word_hits == {"adventure": 1}
    assert project.current_chapter_number == 2


def test_completed_generation_writes_chapter_state_summary(monkeypatch) -> None:
    client, testing_session = make_client()
    token = register_user(client, testing_session, "continuity@example.com", "CONTINUITY")
    story = create_story(client, token)
    submit_words(client, token, story["id"])
    monkeypatch.setattr(GenerationService, "enqueue", lambda self, state: "celery-task-id")

    task_body = client.post(
        f"/api/story-projects/{story['id']}/chapters/1/generate",
        headers=auth_headers(token),
    ).json()

    english_text = "The **adventure** began when the student found a strange map in the old library."
    with testing_session() as session:
        task = session.get(GenerationTask, UUID(task_body["id"]))
        state = GenerationState(
            generation_task_id=str(task.id),
            project_id=story["id"],
            chapter_id=str(task.chapter_id),
            final_status=GenerationStatus.completed,
            retry_count=0,
            draft_output=ChapterGenerationOutput(
                english_content=english_text,
                highlighted_target_words=["adventure"],
                chinese_translation="冒险开始了。",
            ),
            quality_result=QualityReviewResult(word_count=300, passed=True),
        )
        repository = GenerationRepository(session)
        repository.complete_generation_task(state)
        session.commit()

    with testing_session() as session:
        chapter = session.scalar(
            select(Chapter).where(Chapter.chapter_number == 1, Chapter.story_project_id == UUID(story["id"]))
        )
        chapter_state = session.scalar(
            select(ChapterState).where(ChapterState.chapter_id == chapter.id)
        )

    assert chapter_state is not None
    assert chapter_state.summary == english_text[:200]
