from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.session import get_db
from app.domain.generation.repository import GenerationRepository, quality_result_for_report
from app.domain.generation.service import GenerationError, GenerationService
from app.models.auth import User
from app.models.generation import GenerationTask
from app.models.story import Chapter
from app.schemas.generation import (
    ChapterGenerationResultResponse,
    GenerationTaskResponse,
    QualityReportResponse,
)
from app.schemas.story import ChapterContentResponse, ChapterOutput
from app.schemas.story import (
    ChapterLatestGenerationTaskResponse,
    ChapterListItemResponse,
    ChapterTargetWordResponse,
)

router = APIRouter(tags=["generation"])


def get_generation_service(session: Session = Depends(get_db)) -> GenerationService:
    return GenerationService(GenerationRepository(session))


@router.post(
    "/api/story-projects/{story_project_id}/chapters/{chapter_number}/generate",
    response_model=GenerationTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_chapter(
    story_project_id: UUID,
    chapter_number: int,
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> GenerationTask:
    try:
        return generation_service.start_generation(current_user, story_project_id, chapter_number)
    except GenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/api/generation-tasks/{task_id}", response_model=GenerationTaskResponse)
def get_generation_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> GenerationTask:
    task = generation_service.get_generation_task(current_user, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation task not found")
    return task


@router.get("/api/story-projects/{story_project_id}/chapters", response_model=list[ChapterListItemResponse])
def list_chapters(
    story_project_id: UUID,
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> list[ChapterListItemResponse]:
    chapters = generation_service.list_chapters(current_user, story_project_id)
    if chapters is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story project not found")
    return [
        serialize_chapter_list_item(chapter, generation_service.repository.get_latest_generation_task(chapter.id))
        for chapter in chapters
    ]


@router.get(
    "/api/story-projects/{story_project_id}/chapters/{chapter_number}",
    response_model=ChapterContentResponse,
)
def get_chapter(
    story_project_id: UUID,
    chapter_number: int,
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> ChapterContentResponse:
    chapter = generation_service.get_chapter_content(current_user, story_project_id, chapter_number)
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter content not found")
    return serialize_chapter_content(chapter)


@router.get(
    "/api/story-projects/{story_project_id}/chapters/{chapter_number}/generation-result",
    response_model=ChapterGenerationResultResponse,
)
def get_chapter_generation_result(
    story_project_id: UUID,
    chapter_number: int,
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> ChapterGenerationResultResponse:
    result = generation_service.get_chapter_generation_result(current_user, story_project_id, chapter_number)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter generation result not found")
    chapter, task, report = result
    return ChapterGenerationResultResponse(
        task=GenerationTaskResponse(
            id=task.id,
            chapter_id=task.chapter_id,
            status=task.status,
            retry_count=task.retry_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            fallback_reason=task.fallback_reason,
        ),
        output=serialize_chapter_content(chapter).output,
        quality_report=QualityReportResponse(
            id=report.id,
            generation_task_id=report.generation_task_id,
            chapter_id=report.chapter_id,
            result=quality_result_for_report(report),
            out_of_syllabus_rate=report.out_of_syllabus_rate,
            out_of_syllabus_words=report.out_of_syllabus_words,
            target_word_hits=report.target_word_hits,
            passed=report.passed,
            created_at=report.created_at,
            review_notes=report.review_notes,
        ),
    )


def serialize_chapter_content(chapter: Chapter) -> ChapterContentResponse:
    highlighted_words = [word.lemma for word in sorted(chapter.target_words, key=lambda item: item.position)]
    return ChapterContentResponse(
        id=chapter.id,
        story_project_id=chapter.story_project_id,
        chapter_number=chapter.chapter_number,
        status=chapter.status,
        output=ChapterOutput(
            english_content=chapter.english_content or "",
            highlighted_target_words=highlighted_words,
            chinese_translation=chapter.chinese_translation or "",
        ),
    )


def serialize_chapter_list_item(
    chapter: Chapter,
    latest_task: GenerationTask | None,
) -> ChapterListItemResponse:
    return ChapterListItemResponse(
        id=chapter.id,
        story_project_id=chapter.story_project_id,
        chapter_number=chapter.chapter_number,
        status=chapter.status,
        target_words=[
            ChapterTargetWordResponse(
                word=word.word,
                lemma=word.lemma,
                source=word.source,
                position=word.position,
            )
            for word in sorted(chapter.target_words, key=lambda item: item.position)
        ],
        has_output=bool(chapter.english_content and chapter.chinese_translation),
        latest_generation_task=(
            ChapterLatestGenerationTaskResponse(
                id=latest_task.id,
                chapter_id=latest_task.chapter_id,
                status=latest_task.status,
                retry_count=latest_task.retry_count,
                created_at=latest_task.created_at,
                updated_at=latest_task.updated_at,
                started_at=latest_task.started_at,
                completed_at=latest_task.completed_at,
                fallback_reason=latest_task.fallback_reason,
            )
            if latest_task
            else None
        ),
    )


def serialize_quality_report(task: GenerationTask) -> QualityReportResponse | None:
    if not task.quality_reports:
        return None
    report = sorted(task.quality_reports, key=lambda item: item.created_at)[-1]
    return QualityReportResponse(
        id=report.id,
        generation_task_id=report.generation_task_id,
        chapter_id=report.chapter_id,
        result=quality_result_for_report(report),
        out_of_syllabus_rate=report.out_of_syllabus_rate,
        out_of_syllabus_words=report.out_of_syllabus_words,
        target_word_hits=report.target_word_hits,
        passed=report.passed,
        created_at=report.created_at,
        review_notes=report.review_notes,
    )
