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
    WEB_NOVEL_FEW_SHOT_GUIDE,
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

    def test_web_novel_prompt_includes_original_few_shot_guide(self):
        prompt = build_chapter_user_prompt(
            target_words=["decision", "chance"],
            style=StoryStyle.web_novel,
            chapter_number=1,
            target_chapter_count=5,
        )

        assert "原创网文 few-shot" in prompt
        assert "压迫感开场" in prompt
        assert "反转爆发" in prompt
        assert "结尾钩子" in prompt
        assert "Mira" in prompt
        assert "Ken" in prompt

    def test_web_novel_prompt_requires_pressure_structure_and_natural_word_usage(self):
        prompt = build_chapter_user_prompt(
            target_words=["exit", "pass", "rate"],
            style=StoryStyle.web_novel,
            chapter_number=1,
            target_chapter_count=5,
        )

        assert "不是普通儿童探险或平铺直叙" in prompt
        assert "章节前 80 个英文词内必须出现压迫感开场" in prompt
        assert "Opening pressure" in prompt
        assert "Escalation" in prompt
        assert "Reversal" in prompt
        assert "不要为了覆盖目标词而硬塞错误词性" in prompt
        assert "如果目标词是名词，就按名词使用" in prompt
        assert "不要复制示例人物名、场景、样例目标词或句子" in prompt

    @pytest.mark.parametrize(
        "style",
        [StoryStyle.science_fiction, StoryStyle.exam_reading],
    )
    def test_non_web_novel_prompt_excludes_web_novel_few_shot(self, style):
        prompt = build_chapter_user_prompt(
            target_words=["decision"],
            style=style,
            chapter_number=1,
            target_chapter_count=1,
        )

        assert "原创网文 few-shot" not in prompt
        assert "压迫感开场" not in prompt
        assert "反转爆发" not in prompt
        assert "结尾钩子" not in prompt

    def test_web_novel_few_shot_avoids_copyrighted_work_markers(self):
        forbidden_markers = [
            "斗破苍穹",
            "武动乾坤",
            "萧炎",
            "林动",
            "斗气",
            "异火",
            "大千世界",
        ]

        for marker in forbidden_markers:
            assert marker not in WEB_NOVEL_FEW_SHOT_GUIDE

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

    def test_build_chapter_user_prompt_includes_chapter_outline(self):
        outline = [
            "Chapter 1: Lily discovers a hidden library beneath the school.",
            "Chapter 2: The library reveals a portal to another world.",
            "Chapter 3: Lily must choose between two worlds.",
        ]
        prompt = build_chapter_user_prompt(
            target_words=["adventure"],
            style=StoryStyle.science_fiction,
            chapter_number=2,
            target_chapter_count=3,
            chapter_outline=outline,
        )
        assert "初始章节大纲" in prompt
        assert "Lily discovers a hidden library" in prompt
        assert "portal to another world" in prompt

    def test_build_chapter_user_prompt_omits_outline_when_none(self):
        prompt = build_chapter_user_prompt(
            target_words=["adventure"],
            style=StoryStyle.science_fiction,
            chapter_number=2,
            target_chapter_count=3,
            chapter_outline=None,
        )
        assert "初始章节大纲" not in prompt


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
