from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.story import Chapter, StoryProject
from app.models.vocabulary import ChapterTargetWord, ExamSyllabus, SyllabusWord
from app.schemas.vocabulary import TargetWordInput


class VocabularyRepository:
    def __init__(self, session: Session):
        self.session = session

    def search_active_syllabus_words(self, query: str, limit: int = 20) -> list[SyllabusWord]:
        normalized = query.strip().lower()
        if not normalized:
            return []
        return list(
            self.session.scalars(
                select(SyllabusWord)
                .join(ExamSyllabus)
                .where(
                    ExamSyllabus.is_active.is_(True),
                    SyllabusWord.lemma.ilike(f"{normalized}%"),
                )
                .order_by(SyllabusWord.lemma)
                .limit(limit)
            )
        )

    def active_syllabus_lemmas(self, lemmas: set[str]) -> set[str]:
        if not lemmas:
            return set()
        return set(
            self.session.scalars(
                select(SyllabusWord.lemma)
                .join(ExamSyllabus)
                .where(
                    ExamSyllabus.is_active.is_(True),
                    SyllabusWord.lemma.in_(lemmas),
                )
            )
        )

    def get_chapter_for_user(
        self,
        user: User,
        story_project_id: UUID,
        chapter_number: int,
    ) -> Chapter | None:
        return self.session.scalar(
            select(Chapter)
            .join(StoryProject)
            .where(
                StoryProject.id == story_project_id,
                StoryProject.user_id == user.id,
                Chapter.chapter_number == chapter_number,
            )
        )

    def replace_chapter_target_words(self, chapter: Chapter, words: list[TargetWordInput]) -> list[ChapterTargetWord]:
        existing_words = list(
            self.session.scalars(
                select(ChapterTargetWord).where(ChapterTargetWord.chapter_id == chapter.id)
            )
        )
        for word in existing_words:
            self.session.delete(word)
        self.session.flush()

        stored_words: list[ChapterTargetWord] = []
        for index, word in enumerate(words, start=1):
            stored = ChapterTargetWord(
                chapter_id=chapter.id,
                word=word.word,
                lemma=word.lemma or word.word.lower(),
                source=word.source.value,
                position=index,
            )
            self.session.add(stored)
            stored_words.append(stored)
        self.session.flush()
        return stored_words
