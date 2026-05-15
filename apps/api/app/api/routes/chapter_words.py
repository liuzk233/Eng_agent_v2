from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.session import get_db
from app.domain.vocabulary.repository import VocabularyRepository
from app.domain.vocabulary.service import VocabularyError, VocabularyService
from app.models.auth import User
from app.models.vocabulary import ChapterTargetWord
from app.schemas.vocabulary import TargetWordsSubmitRequest

router = APIRouter(prefix="/api/story-projects", tags=["chapter-words"])


def get_vocabulary_service(session: Session = Depends(get_db)) -> VocabularyService:
    return VocabularyService(VocabularyRepository(session))


@router.post("/{story_project_id}/chapters/{chapter_number}/words")
def submit_chapter_target_words(
    story_project_id: UUID,
    chapter_number: int,
    payload: TargetWordsSubmitRequest,
    current_user: User = Depends(get_current_user),
    vocabulary_service: VocabularyService = Depends(get_vocabulary_service),
) -> dict:
    try:
        words = vocabulary_service.submit_chapter_target_words(
            current_user,
            story_project_id,
            chapter_number,
            payload,
        )
    except VocabularyError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error

    return {"words": [_serialize_target_word(word) for word in words]}


def _serialize_target_word(word: ChapterTargetWord) -> dict:
    return {
        "word": word.word,
        "lemma": word.lemma,
        "source": word.source,
        "position": word.position,
    }
