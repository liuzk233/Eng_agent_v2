from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from langgraph.graph import END, StateGraph

from app.domain.enums import GenerationStatus, ReviewResult, StoryStyle
from app.domain.review.base import (
    OutOfSyllabusFinding,
    QualityReviewContext,
    QualityReviewResult,
    QualityRule,
    TargetWord,
    run_quality_rules,
)
from app.domain.review.rules.continuity import ContinuityRule
from app.domain.review.rules.length import LengthRule
from app.domain.review.rules.out_of_syllabus import OutOfSyllabusRule
from app.domain.review.rules.target_coverage import TargetCoverageRule
from app.integrations.llm.base import (
    ChapterGenerationInput,
    ChapterGenerationOutput,
    LLMProvider,
    RetryConfig,
)


@dataclass
class GenerationState:
    generation_task_id: str = ""
    project_id: str = ""
    chapter_id: str = ""
    style: str = StoryStyle.web_novel
    target_words: list[str] = field(default_factory=list)
    target_chapter_count: int = 1
    chapter_number: int = 1

    story_bible_characters: dict = field(default_factory=dict)
    story_bible_worldview: str | None = None
    story_bible_main_plot: str | None = None
    story_bible_tone: str | None = None
    story_bible_immutable_facts: dict = field(default_factory=dict)

    chapter_state_summary: str | None = None
    chapter_state_unresolved_hooks: list = field(default_factory=list)
    chapter_state_character_states: dict = field(default_factory=dict)
    chapter_state_continuity_constraints: dict = field(default_factory=dict)

    retry_count: int = 0
    max_retries: int = 3
    max_out_of_syllabus_rate: float = 0.01

    draft_output: ChapterGenerationOutput | None = None
    quality_result: QualityReviewResult | None = None
    out_of_syllabus_rate: float = 0.0
    review_feedback: str = ""
    final_status: str = GenerationStatus.queued
    technical_error: str = ""

    syllabus_lemmas: set[str] = field(default_factory=set)
    syllabus_allowed_forms: dict[str, set[str]] = field(default_factory=dict)
    proper_nouns: set[str] = field(default_factory=set)
    glosses: dict[str, str] = field(default_factory=dict)


def load_context_node(state: GenerationState) -> dict:
    return {"final_status": GenerationStatus.running}


def generate_draft_node(state: GenerationState, *, provider: LLMProvider) -> dict:
    input_data = ChapterGenerationInput(
        story_bible_characters=state.story_bible_characters,
        story_bible_worldview=state.story_bible_worldview,
        story_bible_main_plot=state.story_bible_main_plot,
        story_bible_tone=state.story_bible_tone,
        story_bible_immutable_facts=state.story_bible_immutable_facts,
        chapter_state_summary=state.chapter_state_summary,
        chapter_state_unresolved_hooks=state.chapter_state_unresolved_hooks,
        chapter_state_character_states=state.chapter_state_character_states,
        chapter_state_continuity_constraints=state.chapter_state_continuity_constraints,
        target_words=state.target_words,
        style=StoryStyle(state.style),
        chapter_number=state.chapter_number,
        target_chapter_count=state.target_chapter_count,
    )
    try:
        output, _usage = provider.generate_chapter(input_data)
    except Exception as exc:
        return {
            "draft_output": None,
            "technical_error": f"chapter_generation_failed: {exc}",
            "review_feedback": str(exc),
            "final_status": GenerationStatus.failed_internal,
        }

    if not output.english_content.strip():
        return {
            "draft_output": None,
            "technical_error": "chapter_generation_empty_english_content",
            "review_feedback": "模型返回正文为空",
            "final_status": GenerationStatus.failed_internal,
        }

    return {
        "draft_output": output,
        "technical_error": "",
        "final_status": GenerationStatus.reviewing,
    }


def decide_after_generate(state: GenerationState) -> Literal["review", "retry", "fallback"]:
    if not state.technical_error:
        return "review"

    if state.retry_count < state.max_retries:
        return "retry"

    return "fallback"


def review_node(state: GenerationState) -> dict:
    if state.draft_output is None:
        return {"final_status": GenerationStatus.failed_internal}

    target_word_objects = [
        TargetWord(lemma=w, allowed_forms=set()) for w in state.target_words
    ]

    context = QualityReviewContext(
        english_content=state.draft_output.english_content,
        target_words=target_word_objects,
        syllabus_lemmas=state.syllabus_lemmas,
        syllabus_allowed_forms=state.syllabus_allowed_forms,
        proper_nouns=state.proper_nouns,
        glosses=state.glosses,
    )

    rules: list[QualityRule] = [
        OutOfSyllabusRule(max_rate=state.max_out_of_syllabus_rate),
        TargetCoverageRule(),
        LengthRule(),
    ]
    if state.chapter_number > 1:
        rules.append(
            ContinuityRule(
                story_bible_characters=state.story_bible_characters,
                story_bible_immutable_facts=state.story_bible_immutable_facts,
                previous_chapter_summary=state.chapter_state_summary,
                previous_unresolved_hooks=state.chapter_state_unresolved_hooks,
            )
        )

    result = run_quality_rules(context, rules)

    return {
        "quality_result": result,
        "out_of_syllabus_rate": result.out_of_syllabus_rate,
        "review_feedback": result.review_notes or "",
    }


def decide_after_review(state: GenerationState) -> Literal["accept", "retry", "fallback"]:
    if state.quality_result is None:
        return "fallback"

    return "accept"


def judge_background_words_node(state: GenerationState, *, provider: LLMProvider) -> dict:
    if state.draft_output is None or state.quality_result is None:
        return {
            "technical_error": "background_word_judgement_missing_review_result",
            "final_status": GenerationStatus.failed_internal,
        }

    candidates = [finding.word for finding in state.quality_result.out_of_syllabus_words]
    if not candidates:
        return {"technical_error": ""}

    judge = getattr(provider, "judge_background_words", None)
    if not callable(judge):
        state.quality_result.out_of_syllabus_words = []
        return {"quality_result": state.quality_result, "technical_error": ""}

    try:
        true_words = judge(
            english_content=state.draft_output.english_content,
            candidate_words=candidates,
        )
    except Exception as exc:
        return {
            "technical_error": f"background_word_judgement_failed: {exc}",
            "review_feedback": str(exc),
            "final_status": GenerationStatus.failed_internal,
        }

    state.quality_result.out_of_syllabus_words = [
        OutOfSyllabusFinding(word=word, translation_cn=translation_cn)
        for word, translation_cn in true_words.items()
    ]
    return {"quality_result": state.quality_result, "technical_error": ""}


def decide_after_judgement(state: GenerationState) -> Literal["accept", "retry", "fallback"]:
    if not state.technical_error:
        return "accept"

    if state.retry_count < state.max_retries:
        return "retry"

    return "fallback"


def retry_node(state: GenerationState) -> dict:
    return {
        "retry_count": state.retry_count + 1,
        "technical_error": "",
        "final_status": GenerationStatus.retrying,
    }


def accept_node(state: GenerationState) -> dict:
    return {"final_status": GenerationStatus.completed}


def fallback_node(state: GenerationState) -> dict:
    return {
        "final_status": GenerationStatus.fallback_completed,
        "review_feedback": state.review_feedback or "超过重试上限，降级输出",
    }


def build_chapter_generation_graph(provider: LLMProvider) -> StateGraph:
    graph = StateGraph(GenerationState)

    graph.add_node("load_context", load_context_node)
    graph.add_node("generate_draft", lambda s: generate_draft_node(s, provider=provider))
    graph.add_node("review", review_node)
    graph.add_node("judge_background_words", lambda s: judge_background_words_node(s, provider=provider))
    graph.add_node("retry", retry_node)
    graph.add_node("accept", accept_node)
    graph.add_node("fallback", fallback_node)

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "generate_draft")
    graph.add_conditional_edges("generate_draft", decide_after_generate, {
        "review": "review",
        "retry": "retry",
        "fallback": "fallback",
    })
    graph.add_conditional_edges("review", decide_after_review, {
        "accept": "judge_background_words",
        "retry": "retry",
        "fallback": "fallback",
    })
    graph.add_conditional_edges("judge_background_words", decide_after_judgement, {
        "accept": "accept",
        "retry": "retry",
        "fallback": "fallback",
    })
    graph.add_edge("retry", "generate_draft")
    graph.add_edge("accept", END)
    graph.add_edge("fallback", END)

    return graph


def run_generation(
    state: GenerationState,
    provider: LLMProvider,
) -> GenerationState:
    graph = build_chapter_generation_graph(provider)
    compiled = graph.compile()
    result = compiled.invoke(state)
    if isinstance(result, GenerationState):
        return result
    return GenerationState(**result)
