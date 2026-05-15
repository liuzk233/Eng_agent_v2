from __future__ import annotations

import logging
import time
from uuid import UUID

from app.domain.enums import GenerationStatus
from app.domain.generation.graphs.chapter_generation import (
    GenerationState,
    run_generation,
)
from app.domain.generation.repository import GenerationRepository
from app.integrations.llm.base import LLMProvider
from app.models.auth import User
from app.models.generation import GenerationTask, QualityReport
from app.models.story import Chapter


class GenerationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GenerationService:
    def __init__(
        self,
        repository: GenerationRepository | None = None,
        provider: LLMProvider | None = None,
    ):
        if provider is None:
            from app.integrations.llm.dashscope_provider import create_llm_provider
            provider = create_llm_provider()
        self.repository = repository
        self.provider = provider

    def start_generation(
        self,
        user: User,
        story_project_id: UUID,
        chapter_number: int,
    ) -> GenerationTask:
        if self.repository is None:
            raise RuntimeError("GenerationRepository is required to start generation")

        chapter = self.repository.get_chapter_for_user(user, story_project_id, chapter_number)
        if chapter is None:
            raise GenerationError("Chapter not found", 404)
        if not chapter.target_words:
            raise GenerationError("Target words are required before generation", 422)

        task = self.repository.create_generation_task(chapter)
        state = self.repository.build_generation_state(task)
        self.repository.session.commit()
        self.repository.session.refresh(task)
        self.enqueue(state)
        return task

    def get_generation_task(self, user: User, task_id: UUID) -> GenerationTask | None:
        if self.repository is None:
            raise RuntimeError("GenerationRepository is required to read generation tasks")
        return self.repository.get_generation_task_for_user(user, task_id)

    def get_chapter_content(
        self,
        user: User,
        story_project_id: UUID,
        chapter_number: int,
    ) -> Chapter | None:
        if self.repository is None:
            raise RuntimeError("GenerationRepository is required to read chapters")
        chapter = self.repository.get_chapter_for_user(user, story_project_id, chapter_number)
        if chapter is None or not chapter.english_content or not chapter.chinese_translation:
            return None
        return chapter

    def get_chapter_generation_result(
        self,
        user: User,
        story_project_id: UUID,
        chapter_number: int,
    ) -> tuple[Chapter, GenerationTask, QualityReport] | None:
        if self.repository is None:
            raise RuntimeError("GenerationRepository is required to read generation results")
        chapter = self.get_chapter_content(user, story_project_id, chapter_number)
        if chapter is None:
            return None
        task = self.repository.get_latest_generation_task(chapter.id)
        report = self.repository.get_latest_quality_report(chapter.id)
        if task is None or report is None:
            return None
        return chapter, task, report

    def execute(self, state: GenerationState) -> GenerationState:
        started = time.perf_counter()
        logger.info(
            "generation.started",
            extra={
                "generation_task_id": state.generation_task_id,
                "chapter_id": state.chapter_id,
                "retry_count": state.retry_count,
            },
        )
        result = run_generation(state, self.provider)
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "generation.completed",
            extra={
                "generation_task_id": result.generation_task_id,
                "chapter_id": result.chapter_id,
                "status": result.final_status,
                "retry_count": result.retry_count,
                "out_of_syllabus_rate": result.out_of_syllabus_rate,
                "duration_ms": duration_ms,
            },
        )
        return result

    def enqueue(self, state: GenerationState) -> str:
        from app.domain.generation.tasks import generation_state_to_payload, run_generation_task

        async_result = run_generation_task.delay(generation_state_to_payload(state))
        return str(async_result.id)

    def is_terminal(self, status: str) -> bool:
        return status in (
            GenerationStatus.completed,
            GenerationStatus.fallback_completed,
            GenerationStatus.failed_internal,
        )


logger = logging.getLogger(__name__)
