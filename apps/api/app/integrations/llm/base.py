from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.domain.enums import StoryStyle


@dataclass(frozen=True)
class ChapterGenerationInput:
    story_bible_characters: dict = field(default_factory=dict)
    story_bible_worldview: str | None = None
    story_bible_main_plot: str | None = None
    story_bible_tone: str | None = None
    story_bible_immutable_facts: dict = field(default_factory=dict)
    chapter_state_summary: str | None = None
    chapter_state_unresolved_hooks: list = field(default_factory=list)
    chapter_state_character_states: dict = field(default_factory=dict)
    chapter_state_continuity_constraints: dict = field(default_factory=dict)
    target_words: list[str] = field(default_factory=list)
    style: StoryStyle = StoryStyle.web_novel
    chapter_number: int = 1
    target_chapter_count: int = 1


@dataclass
class ChapterGenerationOutput:
    english_content: str = ""
    highlighted_target_words: list[str] = field(default_factory=list)
    chinese_translation: str = ""


@dataclass
class RetryConfig:
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class UsageRecord:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model_name: str = ""


class LLMProvider(ABC):
    @abstractmethod
    def generate_chapter(
        self,
        input_data: ChapterGenerationInput,
        retry_config: RetryConfig | None = None,
    ) -> tuple[ChapterGenerationOutput, UsageRecord]:
        ...
