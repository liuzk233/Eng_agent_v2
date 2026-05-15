from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.session import get_db
from app.domain.vocabulary.repository import VocabularyRepository
from app.domain.vocabulary.service import VocabularyService
from app.models.auth import User

router = APIRouter(prefix="/api/vocabularies", tags=["vocabularies"])


def get_vocabulary_service(session: Session = Depends(get_db)) -> VocabularyService:
    return VocabularyService(VocabularyRepository(session))


@router.get("")
def search_vocabularies(
    query: str,
    current_user: User = Depends(get_current_user),
    vocabulary_service: VocabularyService = Depends(get_vocabulary_service),
) -> list[dict]:
    words = vocabulary_service.search_words(query)
    return [
        {
            "lemma": word.lemma,
            "allowed_forms": word.allowed_forms,
            "part_of_speech": word.part_of_speech,
            "definition_cn": word.definition_cn,
        }
        for word in words
    ]
