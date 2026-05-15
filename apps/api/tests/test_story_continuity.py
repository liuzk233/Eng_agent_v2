import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.review.base import QualityReviewContext, QualityReviewResult
from app.domain.review.rules.continuity import ContinuityRule
from app.domain.story.continuity import ContinuityRepository, ContinuityService
from app.db.base import Base
from app.models.auth import User
from app.models.story import Chapter, ChapterState, StoryBible, StoryProject


def make_testing_session() -> sessionmaker:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            StoryProject.__table__,
            Chapter.__table__,
            StoryBible.__table__,
            ChapterState.__table__,
        ],
    )
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def seed_project_with_continuity(testing_session: sessionmaker) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    first_chapter_id = uuid.uuid4()
    second_chapter_id = uuid.uuid4()

    with testing_session() as session:
        session.add(User(id=user_id, email=f"{user_id}@example.com", password_hash="hash", is_active=True))
        session.add(
            StoryProject(
                id=project_id,
                user_id=user_id,
                title="Lily's map",
                style="science_fiction",
                target_chapter_count=2,
                current_chapter_number=1,
            )
        )
        session.add_all(
            [
                Chapter(
                    id=first_chapter_id,
                    story_project_id=project_id,
                    chapter_number=1,
                    status="completed",
                ),
                Chapter(
                    id=second_chapter_id,
                    story_project_id=project_id,
                    chapter_number=2,
                    status="draft",
                ),
            ]
        )
        session.add(
            StoryBible(
                story_project_id=project_id,
                characters={"Lily": "protagonist"},
                worldview="fantasy",
                main_plot="discovering ancient secrets",
                tone="adventurous",
                immutable_facts={"village_name": "Oakhaven"},
            )
        )
        session.add(
            ChapterState(
                chapter_id=first_chapter_id,
                summary="Lily found a mysterious map",
                unresolved_hooks=["mysterious map", "hidden garden"],
                character_states={"Lily": "curious"},
                continuity_constraints={"must_continue_map": True},
            )
        )
        session.commit()

    return project_id, first_chapter_id, second_chapter_id


class TestContinuityRule:
    def test_first_chapter_no_continuity_requirements(self):
        rule = ContinuityRule()
        context = QualityReviewContext(english_content="Some story content here.")
        result = QualityReviewResult()
        rule.evaluate(context, result)

        assert result.passed is True
        assert any("first chapter" in note for note in result.notes)

    def test_subsequent_chapter_with_matching_characters(self):
        rule = ContinuityRule(
            story_bible_characters={"Lily": "protagonist", "Tom": "friend"},
            previous_chapter_summary="Lily found a book",
        )
        context = QualityReviewContext(
            english_content="Lily and Tom walked to the library together."
        )
        result = QualityReviewResult()
        rule.evaluate(context, result)

        assert result.passed is True

    def test_subsequent_chapter_with_missing_characters(self):
        rule = ContinuityRule(
            story_bible_characters={"Lily": "protagonist", "Tom": "friend"},
            previous_chapter_summary="Lily found a book",
        )
        context = QualityReviewContext(
            english_content="A stranger appeared at the door."
        )
        result = QualityReviewResult()
        rule.evaluate(context, result)

        assert result.passed is False
        assert "Lily" in result.review_notes
        assert "Tom" in result.review_notes

    def test_subsequent_chapter_partial_characters_present(self):
        rule = ContinuityRule(
            story_bible_characters={"Lily": "protagonist", "Tom": "friend"},
            previous_chapter_summary="Lily found a book",
        )
        context = QualityReviewContext(
            english_content="Lily sat alone reading the ancient book."
        )
        result = QualityReviewResult()
        rule.evaluate(context, result)

        assert result.passed is False
        assert "Tom" in result.review_notes
        assert "Lily" not in result.review_notes.split("missing")[1].split("Tom")[0]

    def test_empty_characters_and_no_previous_summary(self):
        rule = ContinuityRule(
            story_bible_characters={},
            previous_chapter_summary=None,
        )
        context = QualityReviewContext(english_content="Some content.")
        result = QualityReviewResult()
        rule.evaluate(context, result)

        assert result.passed is True
        assert any("first chapter" in note for note in result.notes)

    def test_with_unresolved_hooks_from_previous_chapter(self):
        rule = ContinuityRule(
            story_bible_characters={"Lily": "protagonist"},
            previous_chapter_summary="Lily found a mysterious map",
            previous_unresolved_hooks=["mysterious map", "hidden garden"],
        )
        context = QualityReviewContext(
            english_content="Lily followed the path described on the map."
        )
        result = QualityReviewResult()
        rule.evaluate(context, result)

        assert result.passed is True


class TestContinuityService:
    def test_get_continuity_context_first_chapter(self):
        testing_session = make_testing_session()
        with testing_session() as session:
            repo = ContinuityRepository(session=session)
            service = ContinuityService(repository=repo)
            ctx = service.get_continuity_context(
                story_project_id=uuid.uuid4(),
                chapter_number=1,
            )

        assert ctx["story_bible"]["characters"] == {}
        assert ctx["previous_chapter"]["summary"] is None
        assert ctx["previous_chapter"]["unresolved_hooks"] == []

    def test_get_continuity_context_with_bible(self):
        testing_session = make_testing_session()
        project_id, _, _ = seed_project_with_continuity(testing_session)
        with testing_session() as session:
            repo = ContinuityRepository(session=session)
            service = ContinuityService(repository=repo)
            ctx = service.get_continuity_context(
                story_project_id=project_id,
                chapter_number=1,
            )

        assert ctx["story_bible"]["characters"] == {"Lily": "protagonist"}
        assert ctx["story_bible"]["worldview"] == "fantasy"
        assert ctx["story_bible"]["immutable_facts"] == {"village_name": "Oakhaven"}
        assert ctx["previous_chapter"]["summary"] is None

    def test_get_continuity_context_with_previous_chapter_state(self):
        testing_session = make_testing_session()
        project_id, _, _ = seed_project_with_continuity(testing_session)
        with testing_session() as session:
            repo = ContinuityRepository(session=session)
            service = ContinuityService(repository=repo)
            ctx = service.get_continuity_context(
                story_project_id=project_id,
                chapter_number=2,
            )

        assert ctx["previous_chapter"]["summary"] == "Lily found a mysterious map"
        assert ctx["previous_chapter"]["unresolved_hooks"] == ["mysterious map", "hidden garden"]
        assert ctx["previous_chapter"]["character_states"] == {"Lily": "curious"}
        assert ctx["previous_chapter"]["continuity_constraints"] == {"must_continue_map": True}


class TestContinuityRepository:
    def test_get_story_bible_returns_none_when_not_found(self):
        testing_session = make_testing_session()
        with testing_session() as session:
            repo = ContinuityRepository(session=session)
            result = repo.get_story_bible(uuid.uuid4())
        assert result is None

    def test_get_chapter_state_returns_none_when_not_found(self):
        testing_session = make_testing_session()
        with testing_session() as session:
            repo = ContinuityRepository(session=session)
            result = repo.get_chapter_state(uuid.uuid4())
        assert result is None

    def test_get_previous_chapter_state_returns_none_for_first_chapter(self):
        testing_session = make_testing_session()
        project_id, _, _ = seed_project_with_continuity(testing_session)
        with testing_session() as session:
            repo = ContinuityRepository(session=session)
            result = repo.get_previous_chapter_state(
                story_project_id=project_id,
                current_chapter_number=1,
            )
        assert result is None

    def test_get_previous_chapter_state_returns_state_for_same_project_previous_chapter(self):
        testing_session = make_testing_session()
        project_id, first_chapter_id, _ = seed_project_with_continuity(testing_session)
        with testing_session() as session:
            repo = ContinuityRepository(session=session)
            result = repo.get_previous_chapter_state(
                story_project_id=project_id,
                current_chapter_number=2,
            )

        assert result is not None
        assert result.chapter_id == first_chapter_id
        assert result.summary == "Lily found a mysterious map"

    def test_update_story_bible_raises_when_not_found(self):
        testing_session = make_testing_session()
        with testing_session() as session:
            repo = ContinuityRepository(session=session)
            with pytest.raises(ValueError, match="StoryBible not found"):
                repo.update_story_bible(
                    uuid.uuid4(),
                    characters={"Lily": "protagonist"},
                )
