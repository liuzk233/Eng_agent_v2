from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, root_validator, validator

from app.domain.enums import StoryStyle


class CreateStoryProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    style: StoryStyle
    target_chapter_count: int = Field(ge=1)

    @root_validator(skip_on_failure=True)
    def enforce_exam_reading_single_chapter(cls, values: dict) -> dict:
        if values.get("style") == StoryStyle.exam_reading:
            values["target_chapter_count"] = 1
        return values


class StoryProjectResponse(BaseModel):
    id: UUID
    title: str
    style: StoryStyle
    target_chapter_count: int
    current_chapter_number: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ChapterOutput(BaseModel):
    english_content: str = Field(min_length=1)
    highlighted_target_words: list[str] = Field(min_length=1)
    chinese_translation: str = Field(min_length=1)

    @validator("highlighted_target_words")
    @classmethod
    def normalize_highlighted_words(cls, words: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for word in words:
            clean = word.strip().lower()
            if clean and clean not in seen:
                normalized.append(clean)
                seen.add(clean)
        if not normalized:
            raise ValueError("at least one highlighted target word is required")
        return normalized

    @root_validator(skip_on_failure=True)
    def require_markdown_highlights(cls, values: dict) -> dict:
        lowered_content = values.get("english_content", "").lower()
        highlighted_target_words = values.get("highlighted_target_words") or []
        missing = [word for word in highlighted_target_words if f"**{word}" not in lowered_content]
        if missing:
            raise ValueError("english_content must include markdown highlights for target words")
        return values


class ChapterContentResponse(BaseModel):
    id: UUID
    story_project_id: UUID
    chapter_number: int
    status: str
    output: ChapterOutput

    class Config:
        orm_mode = True
