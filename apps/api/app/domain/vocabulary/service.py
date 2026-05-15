from uuid import UUID

from app.domain.enums import TargetWordSource
from app.domain.vocabulary.repository import VocabularyRepository
from app.models.auth import User
from app.models.vocabulary import ChapterTargetWord, SyllabusWord
from app.schemas.vocabulary import TargetWordsSubmitRequest


class VocabularyError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class VocabularyService:
    def __init__(self, repository: VocabularyRepository):
        self.repository = repository

    def search_words(self, query: str) -> list[SyllabusWord]:
        return self.repository.search_active_syllabus_words(query)

    def submit_chapter_target_words(
        self,
        user: User,
        story_project_id: UUID,
        chapter_number: int,
        payload: TargetWordsSubmitRequest,
    ) -> list[ChapterTargetWord]:
        chapter = self.repository.get_chapter_for_user(user, story_project_id, chapter_number)
        if chapter is None:
            raise VocabularyError("Chapter not found", 404)

        library_lemmas = {
            word.lemma or word.word.lower()
            for word in payload.words
            if word.source == TargetWordSource.library
        }
        known_lemmas = self.repository.active_syllabus_lemmas(library_lemmas)
        unknown_library_lemmas = sorted(library_lemmas - known_lemmas)
        if unknown_library_lemmas:
            raise VocabularyError("Library target words must exist in active syllabus", 400)

        stored_words = self.repository.replace_chapter_target_words(chapter, payload.words)
        self.repository.session.commit()
        return stored_words
