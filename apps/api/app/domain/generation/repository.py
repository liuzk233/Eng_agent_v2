from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import GenerationStatus, ReviewResult
from app.domain.generation.graphs.chapter_generation import GenerationState
from app.models.auth import User
from app.models.generation import GenerationTask, QualityReport
from app.models.story import Chapter, ChapterState, StoryBible, StoryProject
from app.models.vocabulary import ChapterTargetWord, ExamSyllabus, SyllabusWord


class GenerationRepository:
    def __init__(self, session: Session):
        self.session = session

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

    def get_generation_task_for_user(
        self,
        user: User,
        task_id: UUID,
    ) -> GenerationTask | None:
        return self.session.scalar(
            select(GenerationTask)
            .join(Chapter)
            .join(StoryProject)
            .where(
                GenerationTask.id == task_id,
                StoryProject.user_id == user.id,
            )
        )

    def list_chapters_for_user(
        self,
        user: User,
        story_project_id: UUID,
    ) -> list[Chapter]:
        return list(
            self.session.scalars(
                select(Chapter)
                .join(StoryProject)
                .where(
                    StoryProject.id == story_project_id,
                    StoryProject.user_id == user.id,
                )
                .order_by(Chapter.chapter_number)
            )
        )

    def create_generation_task(self, chapter: Chapter) -> GenerationTask:
        task = GenerationTask(chapter_id=chapter.id, status=GenerationStatus.queued)
        chapter.status = GenerationStatus.queued
        self.session.add(task)
        self.session.flush()
        return task

    def mark_generation_task_running(self, task_id: UUID) -> GenerationTask | None:
        task = self.session.get(GenerationTask, task_id)
        if task is None:
            return None
        now = datetime.now(timezone.utc)
        task.status = GenerationStatus.running
        task.started_at = task.started_at or now
        task.chapter.status = GenerationStatus.running
        self.session.flush()
        return task

    def mark_generation_task_failed(self, task_id: UUID, error_message: str) -> GenerationTask | None:
        task = self.session.get(GenerationTask, task_id)
        if task is None:
            return None
        now = datetime.now(timezone.utc)
        task.status = GenerationStatus.failed_internal
        task.completed_at = now
        task.fallback_reason = error_message[:500]
        task.chapter.status = GenerationStatus.failed_internal
        self.session.flush()
        return task

    def build_generation_state(self, task: GenerationTask) -> GenerationState:
        chapter = task.chapter
        project = chapter.story_project
        story_bible = self._get_story_bible(project.id)
        previous_state = self._get_previous_chapter_state(project.id, chapter.chapter_number)
        syllabus_words = self._active_syllabus_words()
        target_words = self._chapter_target_words(chapter.id)

        return GenerationState(
            generation_task_id=str(task.id),
            project_id=str(project.id),
            chapter_id=str(chapter.id),
            style=project.style,
            target_words=[word.lemma for word in target_words],
            target_chapter_count=project.target_chapter_count,
            chapter_number=chapter.chapter_number,
            story_bible_characters=story_bible.characters if story_bible else {},
            story_bible_worldview=story_bible.worldview if story_bible else None,
            story_bible_main_plot=story_bible.main_plot if story_bible else None,
            story_bible_tone=story_bible.tone if story_bible else None,
            story_bible_immutable_facts=story_bible.immutable_facts if story_bible else {},
            chapter_state_summary=previous_state.summary if previous_state else None,
            chapter_state_unresolved_hooks=previous_state.unresolved_hooks if previous_state else [],
            chapter_state_character_states=previous_state.character_states if previous_state else {},
            chapter_state_continuity_constraints=previous_state.continuity_constraints if previous_state else {},
            syllabus_lemmas={word.lemma for word in syllabus_words},
            syllabus_allowed_forms={
                word.lemma: set(word.allowed_forms or [])
                for word in syllabus_words
            },
            glosses={
                word.lemma: word.definition_cn
                for word in syllabus_words
                if word.definition_cn
            },
        )

    def complete_generation_task(self, state: GenerationState) -> GenerationTask | None:
        task = self.session.get(GenerationTask, UUID(state.generation_task_id))
        if task is None:
            return None

        now = datetime.now(timezone.utc)
        task.status = state.final_status
        task.retry_count = state.retry_count
        task.completed_at = now
        if state.final_status in (GenerationStatus.fallback_completed, GenerationStatus.failed_internal):
            reason = state.review_feedback or state.technical_error or None
            task.fallback_reason = reason[:500] if reason else None
        else:
            task.fallback_reason = None

        chapter = task.chapter
        chapter.status = state.final_status
        if state.final_status in (GenerationStatus.completed, GenerationStatus.fallback_completed):
            project = chapter.story_project
            project.current_chapter_number = min(
                chapter.chapter_number + 1,
                project.target_chapter_count,
            )
        if state.draft_output is not None:
            chapter.english_content = state.draft_output.english_content
            chapter.chinese_translation = state.draft_output.chinese_translation
            chapter.word_count = state.quality_result.word_count if state.quality_result else None

            existing_state = self.session.scalar(
                select(ChapterState).where(ChapterState.chapter_id == chapter.id)
            )
            if existing_state is None:
                existing_state = ChapterState(chapter_id=chapter.id)
                self.session.add(existing_state)
            existing_state.summary = state.draft_output.english_content[:200]

        if state.quality_result is not None:
            self.session.add(
                QualityReport(
                    generation_task_id=task.id,
                    chapter_id=chapter.id,
                    out_of_syllabus_rate=state.quality_result.out_of_syllabus_rate,
                    out_of_syllabus_words=[
                        {
                            "word": finding.word,
                            "translation_cn": finding.translation_cn,
                        }
                        for finding in state.quality_result.out_of_syllabus_words
                    ],
                    target_word_hits=state.quality_result.target_word_hits,
                    review_notes=state.quality_result.review_notes,
                    passed=state.quality_result.passed,
                )
            )

        self.session.flush()
        return task

    def get_latest_quality_report(self, chapter_id: UUID) -> QualityReport | None:
        return self.session.scalar(
            select(QualityReport)
            .where(QualityReport.chapter_id == chapter_id)
            .order_by(QualityReport.created_at.desc(), QualityReport.id.desc())
        )

    def get_latest_generation_task(self, chapter_id: UUID) -> GenerationTask | None:
        return self.session.scalar(
            select(GenerationTask)
            .where(GenerationTask.chapter_id == chapter_id)
            .order_by(GenerationTask.created_at.desc(), GenerationTask.id.desc())
        )

    def _chapter_target_words(self, chapter_id: UUID) -> list[ChapterTargetWord]:
        return list(
            self.session.scalars(
                select(ChapterTargetWord)
                .where(ChapterTargetWord.chapter_id == chapter_id)
                .order_by(ChapterTargetWord.position)
            )
        )

    def _active_syllabus_words(self) -> list[SyllabusWord]:
        return list(
            self.session.scalars(
                select(SyllabusWord)
                .join(ExamSyllabus)
                .where(ExamSyllabus.is_active.is_(True))
            )
        )

    def _get_story_bible(self, story_project_id: UUID) -> StoryBible | None:
        return self.session.scalar(
            select(StoryBible).where(StoryBible.story_project_id == story_project_id)
        )

    def _get_previous_chapter_state(
        self,
        story_project_id: UUID,
        current_chapter_number: int,
    ) -> ChapterState | None:
        if current_chapter_number <= 1:
            return None
        previous_chapter = self.session.scalar(
            select(Chapter).where(
                Chapter.story_project_id == story_project_id,
                Chapter.chapter_number == current_chapter_number - 1,
            )
        )
        if previous_chapter is None:
            return None
        return self.session.scalar(
            select(ChapterState).where(ChapterState.chapter_id == previous_chapter.id)
        )


def quality_result_for_report(report: QualityReport) -> ReviewResult:
    if report.passed:
        return ReviewResult.passed
    task_status = report.generation_task.status
    if task_status == GenerationStatus.fallback_completed:
        return ReviewResult.fallback_accepted
    return ReviewResult.retry_required
