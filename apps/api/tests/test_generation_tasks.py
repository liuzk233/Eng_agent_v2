from app.domain.enums import StoryStyle
from app.domain.generation.graphs.chapter_generation import GenerationState
from app.domain.generation.service import GenerationService
from app.domain.generation.tasks import (
    generation_state_from_payload,
    generation_state_to_payload,
)
from app.integrations.llm.fake_provider import FakeLLMProvider


class FakeAsyncResult:
    id = "queued-task-123"


class FakeCeleryTask:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def delay(self, payload: dict) -> FakeAsyncResult:
        self.payloads.append(payload)
        return FakeAsyncResult()


def make_generation_state() -> GenerationState:
    return GenerationState(
        generation_task_id="generation-task-1",
        project_id="project-1",
        chapter_id="chapter-1",
        style=StoryStyle.science_fiction,
        target_words=["adventure"],
        chapter_number=2,
        target_chapter_count=3,
        syllabus_lemmas={"student", "learn"},
        syllabus_allowed_forms={"learn": {"learns", "learned"}},
        proper_nouns={"Lily"},
    )


def test_generation_state_payload_is_json_safe() -> None:
    payload = generation_state_to_payload(make_generation_state())

    assert payload["syllabus_lemmas"] == ["learn", "student"]
    assert payload["syllabus_allowed_forms"] == {"learn": ["learned", "learns"]}
    assert payload["proper_nouns"] == ["Lily"]


def test_generation_state_payload_restores_set_fields() -> None:
    restored = generation_state_from_payload(generation_state_to_payload(make_generation_state()))

    assert restored.syllabus_lemmas == {"student", "learn"}
    assert restored.syllabus_allowed_forms == {"learn": {"learns", "learned"}}
    assert restored.proper_nouns == {"Lily"}


def test_generation_service_enqueue_defers_work_to_celery(monkeypatch) -> None:
    fake_task = FakeCeleryTask()
    monkeypatch.setattr("app.domain.generation.tasks.run_generation_task", fake_task)
    service = GenerationService(provider=FakeLLMProvider(should_fail=True))

    task_id = service.enqueue(make_generation_state())

    assert task_id == "queued-task-123"
    assert len(fake_task.payloads) == 1
    assert fake_task.payloads[0]["generation_task_id"] == "generation-task-1"
