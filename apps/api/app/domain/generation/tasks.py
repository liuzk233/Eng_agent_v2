from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from celery import Celery

from app.core.config import settings
from app.domain.generation.graphs.chapter_generation import GenerationState


celery_app = Celery(
    "vocabulary_story_learning_generation",
    broker=settings.resolved_celery_broker_url(),
    backend=settings.resolved_celery_result_backend(),
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)


def generation_state_to_payload(state: GenerationState) -> dict[str, Any]:
    return _json_safe(asdict(state))


def generation_state_from_payload(payload: dict[str, Any]) -> GenerationState:
    normalized = dict(payload)
    normalized["syllabus_lemmas"] = set(normalized.get("syllabus_lemmas") or [])
    normalized["proper_nouns"] = set(normalized.get("proper_nouns") or [])
    normalized["syllabus_allowed_forms"] = {
        lemma: set(forms)
        for lemma, forms in (normalized.get("syllabus_allowed_forms") or {}).items()
    }
    return GenerationState(**normalized)


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted(_json_safe(item) for item in value)
    return value


@celery_app.task(name="generation.run_chapter")
def run_generation_task(payload: dict[str, Any]) -> dict[str, Any]:
    import logging
    from uuid import UUID

    from app.db.session import SessionLocal
    from app.domain.generation.repository import GenerationRepository
    from app.domain.generation.service import GenerationService

    logger = logging.getLogger(__name__)

    raw_task_id = payload.get("generation_task_id")
    task_id: UUID | None = None
    if raw_task_id is not None:
        try:
            task_id = UUID(str(raw_task_id))
        except (ValueError, TypeError):
            pass

    try:
        state = generation_state_from_payload(payload)
        if task_id is None:
            task_id = UUID(state.generation_task_id)

        with SessionLocal() as session:
            repository = GenerationRepository(session)
            repository.mark_generation_task_running(task_id)
            session.commit()

        result = GenerationService().execute(state)

        with SessionLocal() as session:
            repository = GenerationRepository(session)
            repository.complete_generation_task(result)
            session.commit()

        return generation_state_to_payload(result)
    except Exception as exc:
        task_id_str = str(task_id) if task_id is not None else "<unidentifiable>"
        logger.exception(
            "generation.task_failed",
            extra={"generation_task_id": task_id_str},
        )
        if task_id is not None:
            with SessionLocal() as session:
                repository = GenerationRepository(session)
                repository.mark_generation_task_failed(task_id, str(exc))
                session.commit()
            return generation_state_to_payload(GenerationState(
                generation_task_id=str(task_id),
            ))
        raise
