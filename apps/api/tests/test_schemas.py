from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import GenerationStatus, ReviewResult, StoryStyle, TargetWordSource
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.generation import GenerationTaskResponse, QualityReportResponse
from app.schemas.progress import LearningProgressResponse
from app.schemas.story import (
    ChapterContentResponse,
    ChapterOutput,
    CreateStoryProjectRequest,
    StoryProjectResponse,
)
from app.schemas.vocabulary import TargetWordInput, TargetWordsSubmitRequest


def test_story_style_enum_is_closed_to_three_values() -> None:
    assert {style.value for style in StoryStyle} == {
        "web_novel",
        "science_fiction",
        "exam_reading",
    }


def test_exam_reading_story_request_forces_single_chapter() -> None:
    request = CreateStoryProjectRequest(
        title="Reading practice",
        style=StoryStyle.exam_reading,
        target_chapter_count=9,
    )

    assert request.target_chapter_count == 1


def test_serial_story_request_requires_positive_chapter_count() -> None:
    with pytest.raises(ValidationError):
        CreateStoryProjectRequest(
            title="Progression tale",
            style=StoryStyle.web_novel,
            target_chapter_count=0,
        )

    valid = CreateStoryProjectRequest(
        title="Mars station",
        style=StoryStyle.science_fiction,
        target_chapter_count=6,
    )
    assert valid.target_chapter_count == 6


def test_target_words_request_caps_words_and_normalizes_mixed_sources() -> None:
    request = TargetWordsSubmitRequest(
        words=[
            TargetWordInput(word="achieve", source=TargetWordSource.manual),
            TargetWordInput(word="Achieve", source=TargetWordSource.library),
            TargetWordInput(word="analysis", source=TargetWordSource.library),
        ]
    )

    assert [word.lemma for word in request.words] == ["achieve", "analysis"]
    assert request.words[0].source == TargetWordSource.manual
    assert request.words[1].source == TargetWordSource.library

    with pytest.raises(ValidationError):
        TargetWordsSubmitRequest(
            words=[
                TargetWordInput(word=f"word-{index}", source=TargetWordSource.manual)
                for index in range(11)
            ]
        )


def test_chapter_output_requires_standard_modules() -> None:
    output = ChapterOutput(
        english_content="The hero **achieved** a quiet victory.",
        highlighted_target_words=["achieve"],
        chinese_translation="英雄取得了一场安静的胜利。",
    )

    assert "**achieved**" in output.english_content
    assert output.highlighted_target_words == ["achieve"]

    with pytest.raises(ValidationError):
        ChapterOutput(
            english_content="No highlight here.",
            highlighted_target_words=["achieve"],
            chinese_translation="这里没有高亮。",
        )


def test_generation_status_and_review_response_cover_retry_and_fallback() -> None:
    assert {status.value for status in GenerationStatus} == {
        "queued",
        "running",
        "reviewing",
        "retrying",
        "completed",
        "fallback_completed",
        "failed_internal",
    }
    assert {result.value for result in ReviewResult} == {
        "passed",
        "retry_required",
        "fallback_accepted",
    }

    task = GenerationTaskResponse(
        id=uuid4(),
        chapter_id=uuid4(),
        status=GenerationStatus.fallback_completed,
        retry_count=4,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        fallback_reason="out_of_syllabus_retry_limit",
    )
    assert task.status == GenerationStatus.fallback_completed

    with pytest.raises(ValidationError):
        GenerationTaskResponse(
            id=uuid4(),
            chapter_id=uuid4(),
            status=GenerationStatus.retrying,
            retry_count=4,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


def test_quality_report_bounds_out_of_syllabus_rate() -> None:
    report = QualityReportResponse(
        id=uuid4(),
        generation_task_id=uuid4(),
        chapter_id=uuid4(),
        result=ReviewResult.passed,
        out_of_syllabus_rate=0.01,
        out_of_syllabus_words=[{"word": "schadenfreude", "translation_cn": "幸灾乐祸"}],
        target_word_hits={"achieve": 2},
        passed=True,
        created_at=datetime.now(timezone.utc),
    )

    assert report.out_of_syllabus_rate == 0.01

    with pytest.raises(ValidationError):
        QualityReportResponse(
            id=uuid4(),
            generation_task_id=uuid4(),
            chapter_id=uuid4(),
            result=ReviewResult.passed,
            out_of_syllabus_rate=1.5,
            out_of_syllabus_words=[],
            target_word_hits={},
            passed=True,
            created_at=datetime.now(timezone.utc),
        )


def test_auth_and_story_responses_are_serializable_contracts() -> None:
    user = UserResponse(
        id=uuid4(),
        email="student@example.com",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    token = TokenResponse(access_token="jwt-token")
    register = RegisterRequest(
        email="student@example.com",
        password="strong-password",
        invite_code="INVITE-2026",
    )
    login = LoginRequest(email="student@example.com", password="strong-password")
    admin_login = LoginRequest(email="admin138", password="0507138")
    project = StoryProjectResponse(
        id=uuid4(),
        title="Mars station",
        style=StoryStyle.science_fiction,
        target_chapter_count=3,
        current_chapter_number=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    chapter = ChapterContentResponse(
        id=uuid4(),
        story_project_id=project.id,
        chapter_number=1,
        status="completed",
        output=ChapterOutput(
            english_content="The pilot **achieved** orbit.",
            highlighted_target_words=["achieve"],
            chinese_translation="飞行员进入了轨道。",
        ),
    )

    assert user.email == register.email == login.email
    assert admin_login.email == "admin138"
    assert token.token_type == "bearer"
    assert project.style == StoryStyle.science_fiction
    assert chapter.output.chinese_translation


def test_learning_progress_response_captures_word_review_state() -> None:
    progress = LearningProgressResponse(
        id=uuid4(),
        user_id=uuid4(),
        lemma="achieve",
        encounter_count=3,
        last_seen_chapter_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    assert progress.lemma == "achieve"
    assert progress.encounter_count == 3
