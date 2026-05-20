from importlib import metadata

from app.domain.enums import GenerationStatus, StoryStyle
from app.domain.generation.graphs.chapter_generation import (
    GenerationState,
    decide_after_review,
    run_generation,
)
from app.domain.review.base import QualityReviewResult
from app.integrations.llm.base import (
    ChapterGenerationInput,
    ChapterGenerationOutput,
    LLMProvider,
    RetryConfig,
    UsageRecord,
)
from app.integrations.llm.fake_provider import FakeLLMProvider


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def make_state(**overrides) -> GenerationState:
    defaults = {
        "generation_task_id": "test-task-001",
        "project_id": "test-project-001",
        "chapter_id": "test-chapter-001",
        "style": StoryStyle.web_novel,
        "target_words": ["adventure", "courage"],
        "chapter_number": 1,
        "target_chapter_count": 5,
        "max_out_of_syllabus_rate": 1.0,
    }
    return GenerationState(**{**defaults, **overrides})


class RecordingFakeLLMProvider(FakeLLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self.inputs: list[ChapterGenerationInput] = []

    def generate_chapter(
        self,
        input_data: ChapterGenerationInput,
        retry_config: RetryConfig | None = None,
    ) -> tuple[ChapterGenerationOutput, UsageRecord]:
        self.inputs.append(input_data)
        return super().generate_chapter(input_data, retry_config)


class StaticLLMProvider(LLMProvider):
    def __init__(self, english_content: str) -> None:
        self.english_content = english_content
        self.call_count = 0

    def generate_chapter(
        self,
        input_data: ChapterGenerationInput,
        retry_config: RetryConfig | None = None,
    ) -> tuple[ChapterGenerationOutput, UsageRecord]:
        self.call_count += 1
        return (
            ChapterGenerationOutput(
                english_content=self.english_content,
                highlighted_target_words=list(input_data.target_words),
                chinese_translation="这是一段可重复的测试译文。",
            ),
            UsageRecord(
                prompt_tokens=20,
                completion_tokens=80,
                total_tokens=100,
                model_name="static-test-provider",
            ),
        )


class FailingThenStaticLLMProvider(StaticLLMProvider):
    def __init__(self, english_content: str, *, fail_times: int) -> None:
        super().__init__(english_content)
        self.fail_times = fail_times
        self.attempts = 0

    def generate_chapter(
        self,
        input_data: ChapterGenerationInput,
        retry_config: RetryConfig | None = None,
    ) -> tuple[ChapterGenerationOutput, UsageRecord]:
        self.attempts += 1
        if self.attempts <= self.fail_times:
            raise RuntimeError("temporary provider failure")
        return super().generate_chapter(input_data, retry_config)


class JudgingStaticLLMProvider(StaticLLMProvider):
    def __init__(
        self,
        english_content: str,
        judgement_result: dict[str, str] | None = None,
        *,
        judgement_fail_times: int = 0,
    ) -> None:
        super().__init__(english_content)
        self.judgement_result = judgement_result or {}
        self.judgement_fail_times = judgement_fail_times
        self.judgement_attempts = 0
        self.judged_candidates: list[str] = []

    def judge_background_words(
        self,
        *,
        english_content: str,
        candidate_words: list[str],
    ) -> dict[str, str]:
        self.judgement_attempts += 1
        self.judged_candidates = list(candidate_words)
        if self.judgement_attempts <= self.judgement_fail_times:
            raise RuntimeError("temporary judgement failure")
        return dict(self.judgement_result)


def compliant_english_content(target_word: str = "adventure") -> str:
    opening = f"The student will learn {target_word} with a friend today."
    repeated = "The student will learn with a friend at school today."
    return " ".join([opening, *([repeated] * 30)])


def compliant_syllabus_lemmas() -> set[str]:
    return {"the", "student", "will", "learn", "with", "a", "friend", "at", "school", "today"}


class TestDecideAfterReview:
    def test_accept_when_passed(self):
        state = make_state()
        state.quality_result = QualityReviewResult(passed=True)
        assert decide_after_review(state) == "accept"

    def test_accept_when_not_passed_because_quality_failures_do_not_retry(self):
        state = make_state()
        state.quality_result = QualityReviewResult(passed=False)
        state.retry_count = 0
        assert decide_after_review(state) == "accept"

    def test_accept_when_not_passed_and_max_retries_exceeded(self):
        state = make_state()
        state.quality_result = QualityReviewResult(passed=False)
        state.retry_count = 3
        assert decide_after_review(state) == "accept"

    def test_fallback_when_no_quality_result(self):
        state = make_state()
        state.quality_result = None
        assert decide_after_review(state) == "fallback"


class TestGenerationGraphEndToEnd:
    def test_langgraph_dependencies_are_patched_above_known_cve_floor(self):
        assert version_tuple(metadata.version("langgraph")) >= (1, 0, 10)
        assert version_tuple(metadata.version("langgraph-checkpoint")) >= (4, 0, 0)

    def test_first_chapter_completes_with_fake_provider(self):
        provider = FakeLLMProvider()
        state = make_state(target_words=["adventure", "courage"])
        result = run_generation(state, provider)

        assert result.final_status == GenerationStatus.completed
        assert result.draft_output is not None
        assert result.quality_result is not None

    def test_completed_output_has_english_content(self):
        provider = FakeLLMProvider()
        state = make_state(target_words=["adventure"])
        result = run_generation(state, provider)

        assert result.draft_output is not None
        assert len(result.draft_output.english_content) > 0
        assert "**adventure**" in result.draft_output.english_content

    def test_completed_output_has_chinese_translation(self):
        provider = FakeLLMProvider()
        state = make_state(target_words=["adventure"])
        result = run_generation(state, provider)

        assert result.draft_output is not None
        assert len(result.draft_output.chinese_translation) > 0

    def test_completed_output_has_highlighted_target_words(self):
        provider = FakeLLMProvider()
        state = make_state(target_words=["adventure", "courage"])
        result = run_generation(state, provider)

        assert result.draft_output is not None
        assert "adventure" in result.draft_output.highlighted_target_words
        assert "courage" in result.draft_output.highlighted_target_words

    def test_syllabus_check_with_low_out_of_syllabus_rate(self):
        provider = StaticLLMProvider(compliant_english_content("adventure"))
        state = make_state(
            target_words=["adventure"],
            syllabus_lemmas=compliant_syllabus_lemmas(),
            max_out_of_syllabus_rate=0.01,
        )
        result = run_generation(state, provider)

        assert result.final_status == GenerationStatus.completed
        assert result.quality_result is not None
        assert result.quality_result.passed is True
        assert result.out_of_syllabus_rate <= 0.01
        assert result.quality_result.out_of_syllabus_words == []
        assert result.quality_result.target_word_hits == {"adventure": 1}

    def test_high_out_of_syllabus_rate_completes_without_regenerating_body(self):
        provider = StaticLLMProvider(compliant_english_content("adventure"))
        state = make_state(
            target_words=["adventure"],
            syllabus_lemmas=set(),
            max_out_of_syllabus_rate=0.001,
            max_retries=1,
        )
        result = run_generation(state, provider)

        assert result.final_status == GenerationStatus.completed
        assert result.retry_count == 0
        assert result.out_of_syllabus_rate > state.max_out_of_syllabus_rate
        assert provider.call_count == 1

    def test_quality_review_failure_does_not_fallback_after_max_retries(self):
        provider = FakeLLMProvider()
        state = make_state(
            target_words=["adventure"],
            syllabus_lemmas=set(),
            max_out_of_syllabus_rate=0.0001,
            max_retries=0,
        )
        result = run_generation(state, provider)

        assert result.final_status == GenerationStatus.completed
        assert result.draft_output is not None
        assert result.retry_count == 0
        assert result.out_of_syllabus_rate > state.max_out_of_syllabus_rate

    def test_technical_generation_failure_retries_and_then_completes(self):
        provider = FailingThenStaticLLMProvider(compliant_english_content("adventure"), fail_times=1)
        state = make_state(
            target_words=["adventure"],
            syllabus_lemmas=compliant_syllabus_lemmas(),
            max_retries=2,
        )
        result = run_generation(state, provider)

        assert result.retry_count == 1
        assert result.final_status == GenerationStatus.completed
        assert provider.attempts == 2

    def test_true_background_words_keep_chinese_translation_after_judgement(self):
        provider = JudgingStaticLLMProvider(
            compliant_english_content("adventure").replace("with a friend", "with lint"),
            {"lint": "粘毛"},
        )
        state = make_state(
            target_words=["adventure"],
            syllabus_lemmas=compliant_syllabus_lemmas(),
            max_out_of_syllabus_rate=0.001,
        )
        result = run_generation(state, provider)

        assert result.final_status == GenerationStatus.completed
        assert result.quality_result is not None
        assert [(word.word, word.translation_cn) for word in result.quality_result.out_of_syllabus_words] == [
            ("lint", "粘毛")
        ]
        assert "lint" in provider.judged_candidates

    def test_non_true_background_candidates_are_not_annotated(self):
        provider = JudgingStaticLLMProvider(
            compliant_english_content("adventure").replace("with a friend", "with robot"),
            {},
        )
        state = make_state(
            target_words=["adventure"],
            syllabus_lemmas=compliant_syllabus_lemmas(),
            max_out_of_syllabus_rate=0.001,
        )
        result = run_generation(state, provider)

        assert result.final_status == GenerationStatus.completed
        assert result.quality_result is not None
        assert result.quality_result.out_of_syllabus_words == []
        assert "robot" in provider.judged_candidates

    def test_background_word_judgement_technical_failure_retries(self):
        provider = JudgingStaticLLMProvider(
            compliant_english_content("adventure").replace("with a friend", "with lint"),
            {"lint": "粘毛"},
            judgement_fail_times=1,
        )
        state = make_state(
            target_words=["adventure"],
            syllabus_lemmas=compliant_syllabus_lemmas(),
            max_out_of_syllabus_rate=0.001,
            max_retries=2,
        )
        result = run_generation(state, provider)

        assert result.final_status == GenerationStatus.completed
        assert result.retry_count == 1
        assert provider.call_count == 2
        assert provider.judgement_attempts == 2

    def test_continuity_rule_applied_for_subsequent_chapter(self):
        provider = RecordingFakeLLMProvider()
        state = make_state(
            target_words=["adventure"],
            chapter_number=2,
            story_bible_characters={"Lily": "protagonist"},
            story_bible_worldview="fantasy village",
            chapter_state_summary="Lily found a mysterious book",
        )
        result = run_generation(state, provider)

        assert result.draft_output is not None
        assert result.final_status == GenerationStatus.completed
        assert provider.inputs
        first_input = provider.inputs[0]
        assert first_input.chapter_number == 2
        assert first_input.story_bible_characters == {"Lily": "protagonist"}
        assert first_input.story_bible_worldview == "fantasy village"
        assert first_input.chapter_state_summary == "Lily found a mysterious book"
        assert "Lily" in result.draft_output.english_content

    def test_exam_reading_style(self):
        provider = RecordingFakeLLMProvider()
        state = make_state(
            target_words=["knowledge"],
            style=StoryStyle.exam_reading,
            target_chapter_count=1,
            chapter_number=1,
        )
        result = run_generation(state, provider)

        assert result.draft_output is not None
        assert result.final_status == GenerationStatus.completed
        assert provider.inputs
        assert provider.inputs[0].style == StoryStyle.exam_reading
        assert provider.inputs[0].target_chapter_count == 1
        assert result.draft_output.english_content.startswith("In modern society")
