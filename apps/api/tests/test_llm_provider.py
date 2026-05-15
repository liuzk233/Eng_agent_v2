import pytest

from app.domain.enums import StoryStyle
from app.integrations.llm.base import (
    ChapterGenerationInput,
    ChapterGenerationOutput,
    LLMProvider,
    RetryConfig,
    UsageRecord,
)
from app.integrations.llm.fake_provider import FakeLLMProvider
from app.integrations.llm.prompts import (
    CHAPTER_GENERATION_SYSTEM_PROMPT,
    STYLE_NAMES,
    build_chapter_user_prompt,
)


class TestLLMProviderContract:
    def test_llm_provider_is_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider()

    def test_fake_provider_returns_chapter_output(self):
        provider = FakeLLMProvider()
        input_data = ChapterGenerationInput(
            target_words=["adventure", "courage"],
            style=StoryStyle.web_novel,
            chapter_number=1,
            target_chapter_count=5,
        )
        output, usage = provider.generate_chapter(input_data)

        assert isinstance(output, ChapterGenerationOutput)
        assert isinstance(usage, UsageRecord)

    def test_fake_provider_english_contains_target_words(self):
        provider = FakeLLMProvider()
        input_data = ChapterGenerationInput(
            target_words=["adventure", "courage"],
            style=StoryStyle.web_novel,
            chapter_number=1,
        )
        output, _ = provider.generate_chapter(input_data)

        for word in input_data.target_words:
            assert f"**{word}" in output.english_content, f"Target word '{word}' not highlighted"

    def test_fake_provider_returns_highlighted_target_words(self):
        provider = FakeLLMProvider()
        input_data = ChapterGenerationInput(
            target_words=["adventure", "courage"],
            style=StoryStyle.web_novel,
        )
        output, _ = provider.generate_chapter(input_data)

        assert output.highlighted_target_words == ["adventure", "courage"]

    def test_fake_provider_returns_chinese_translation(self):
        provider = FakeLLMProvider()
        input_data = ChapterGenerationInput(
            target_words=["adventure"],
            style=StoryStyle.web_novel,
        )
        output, _ = provider.generate_chapter(input_data)

        assert len(output.chinese_translation) > 0
        assert "冒险" in output.chinese_translation

    def test_fake_provider_returns_usage_record(self):
        provider = FakeLLMProvider()
        output, usage = provider.generate_chapter(ChapterGenerationInput())

        assert usage.total_tokens > 0
        assert usage.model_name == "fake-provider-v1"

    def test_fake_provider_tracks_call_count(self):
        provider = FakeLLMProvider()
        assert provider.call_count == 0

        provider.generate_chapter(ChapterGenerationInput())
        assert provider.call_count == 1

        provider.generate_chapter(ChapterGenerationInput())
        assert provider.call_count == 2

    def test_fake_provider_can_be_configured_to_fail(self):
        provider = FakeLLMProvider(should_fail=True)
        with pytest.raises(RuntimeError, match="configured to fail"):
            provider.generate_chapter(ChapterGenerationInput())

    def test_fake_provider_exam_reading_style(self):
        provider = FakeLLMProvider()
        input_data = ChapterGenerationInput(
            target_words=["knowledge"],
            style=StoryStyle.exam_reading,
        )
        output, _ = provider.generate_chapter(input_data)

        assert "modern society" in output.english_content

    def test_fake_provider_with_story_bible_context(self):
        provider = FakeLLMProvider()
        input_data = ChapterGenerationInput(
            target_words=["adventure"],
            style=StoryStyle.science_fiction,
            chapter_number=2,
            story_bible_characters={"Lily": "protagonist"},
            story_bible_worldview="A future where books are forbidden",
            chapter_state_summary="Lily found a hidden library",
        )
        output, _ = provider.generate_chapter(input_data)

        assert len(output.english_content) > 0
        assert "**adventure**" in output.english_content


class TestPrompts:
    def test_style_names_contains_all_styles(self):
        assert StoryStyle.web_novel in STYLE_NAMES
        assert StoryStyle.science_fiction in STYLE_NAMES
        assert StoryStyle.exam_reading in STYLE_NAMES

    def test_build_chapter_user_prompt_includes_target_words(self):
        prompt = build_chapter_user_prompt(
            target_words=["adventure", "courage"],
            style=StoryStyle.web_novel,
            chapter_number=1,
            target_chapter_count=5,
        )
        assert "adventure" in prompt
        assert "courage" in prompt
        assert "网络爽文" in prompt

    def test_build_chapter_user_prompt_first_chapter(self):
        prompt = build_chapter_user_prompt(
            target_words=["adventure"],
            style=StoryStyle.web_novel,
            chapter_number=1,
            target_chapter_count=3,
        )
        assert "第一章" in prompt

    def test_build_chapter_user_prompt_subsequent_chapter(self):
        prompt = build_chapter_user_prompt(
            target_words=["adventure"],
            style=StoryStyle.web_novel,
            chapter_number=2,
            target_chapter_count=3,
            previous_chapter_summary="Lily discovered a map",
        )
        assert "延续前文" in prompt

    def test_system_prompt_is_defined(self):
        assert len(CHAPTER_GENERATION_SYSTEM_PROMPT) > 0
        assert "JSON" in CHAPTER_GENERATION_SYSTEM_PROMPT


class TestChapterGenerationInput:
    def test_default_values(self):
        data = ChapterGenerationInput()
        assert data.style == StoryStyle.web_novel
        assert data.chapter_number == 1
        assert data.target_words == []
        assert data.story_bible_characters == {}

    def test_with_all_fields(self):
        data = ChapterGenerationInput(
            target_words=["adventure"],
            style=StoryStyle.science_fiction,
            chapter_number=3,
            story_bible_characters={"Lily": "protagonist"},
            story_bible_worldview="dystopian future",
            chapter_state_summary="Lily found a clue",
        )
        assert data.target_words == ["adventure"]
        assert data.style == StoryStyle.science_fiction
