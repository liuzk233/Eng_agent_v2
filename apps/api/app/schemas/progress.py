from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LearningProgressResponse(BaseModel):
    id: UUID
    user_id: UUID
    lemma: str = Field(min_length=1, max_length=120)
    encounter_count: int = Field(ge=0)
    last_seen_chapter_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
