from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, root_validator

from app.domain.enums import GenerationStatus, ReviewResult
from app.schemas.story import ChapterOutput


class GenerateChapterRequest(BaseModel):
    chapter_id: UUID


class GenerationTaskResponse(BaseModel):
    id: UUID
    chapter_id: UUID
    status: GenerationStatus
    retry_count: int = Field(ge=0, le=4)
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    fallback_reason: str | None = None

    @root_validator(skip_on_failure=True)
    def enforce_retry_and_fallback_state(cls, values: dict) -> dict:
        if values.get("status") == GenerationStatus.retrying and values.get("retry_count", 0) > 3:
            raise ValueError("retrying status cannot exceed retry_count 3")
        if values.get("status") == GenerationStatus.fallback_completed and not values.get("fallback_reason"):
            raise ValueError("fallback_completed requires fallback_reason")
        return values

    class Config:
        orm_mode = True


class OutOfSyllabusWord(BaseModel):
    word: str = Field(min_length=1)
    translation_cn: str = Field(min_length=1)


class QualityReportResponse(BaseModel):
    id: UUID
    generation_task_id: UUID
    chapter_id: UUID
    result: ReviewResult
    out_of_syllabus_rate: float = Field(ge=0, le=1)
    out_of_syllabus_words: list[OutOfSyllabusWord]
    target_word_hits: dict[str, int]
    passed: bool
    created_at: datetime
    review_notes: str | None = None

    class Config:
        orm_mode = True


class ChapterGenerationResultResponse(BaseModel):
    task: GenerationTaskResponse
    output: ChapterOutput
    quality_report: QualityReportResponse
