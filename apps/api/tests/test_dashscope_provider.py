import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.domain.enums import StoryStyle
from app.integrations.llm.prompts import CHAPTER_GENERATION_SYSTEM_PROMPT
from app.integrations.llm.base import (
    ChapterGenerationInput,
    ChapterGenerationOutput,
    RetryConfig,
    UsageRecord,
)
from app.integrations.llm.dashscope_provider import DashScopeProvider, create_llm_provider


def _mock_api_response(
    english: str = "The **adventure** began.",
    words: list[str] | None = None,
    chinese: str = "冒险开始了。",
    prompt_tokens: int = 200,
    completion_tokens: int = 400,
) -> dict:
    words = words or ["adventure"]
    content = json.dumps({
        "english_content": english,
        "highlighted_target_words": words,
        "chinese_translation": chinese,
    })
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


class TestDashScopeProvider:
    def test_generate_chapter_returns_output_and_usage(self):
        provider = DashScopeProvider(api_key="test-key", base_url="https://fake-api.test", model="test-model")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _mock_api_response()

        with patch("httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)

            input_data = ChapterGenerationInput(
                target_words=["adventure"],
                style=StoryStyle.web_novel,
                chapter_number=1,
                target_chapter_count=5,
            )
            output, usage = provider.generate_chapter(input_data)

        assert isinstance(output, ChapterGenerationOutput)
        assert output.english_content == "The **adventure** began."
        assert output.highlighted_target_words == ["adventure"]
        assert output.chinese_translation == "冒险开始了。"
        assert isinstance(usage, UsageRecord)
        assert usage.prompt_tokens == 200
        assert usage.completion_tokens == 400
        assert usage.model_name == "test-model"

    def test_generate_chapter_increments_call_count(self):
        provider = DashScopeProvider(api_key="test-key", base_url="https://fake-api.test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _mock_api_response()

        with patch("httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)

            assert provider.call_count == 0
            provider.generate_chapter(ChapterGenerationInput())
            assert provider.call_count == 1
            provider.generate_chapter(ChapterGenerationInput())
            assert provider.call_count == 2

    def test_generate_chapter_raises_on_api_error(self):
        provider = DashScopeProvider(api_key="test-key", base_url="https://fake-api.test")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(RuntimeError, match="status 500"):
                provider.generate_chapter(ChapterGenerationInput())

    def test_generate_chapter_raises_on_auth_error(self):
        provider = DashScopeProvider(api_key="bad-key", base_url="https://fake-api.test")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(RuntimeError, match="status 401"):
                provider.generate_chapter(ChapterGenerationInput())

    def test_parse_output_handles_json_wrapped_in_code_block(self):
        provider = DashScopeProvider(api_key="test-key", base_url="https://fake-api.test")

        content = '```json\n{"english_content": "Hello **world**.", "highlighted_target_words": ["world"], "chinese_translation": "你好世界。"}\n```'

        result = provider._parse_output(content, ["world"])
        assert result.english_content == "Hello **world**."
        assert result.highlighted_target_words == ["world"]
        assert result.chinese_translation == "你好世界。"

    def test_parse_output_fallback_on_non_json(self):
        provider = DashScopeProvider(api_key="test-key", base_url="https://fake-api.test")

        content = "This is just plain text, not JSON at all."
        result = provider._parse_output(content, ["adventure"])
        assert result.english_content == content
        assert result.highlighted_target_words == ["adventure"]

    def test_build_user_prompt_includes_target_words(self):
        provider = DashScopeProvider(api_key="test-key", base_url="https://fake-api.test")
        input_data = ChapterGenerationInput(
            target_words=["adventure", "courage"],
            style=StoryStyle.science_fiction,
            chapter_number=2,
            target_chapter_count=10,
            story_bible_main_plot="Space exploration",
            story_bible_characters={"Lily": "captain"},
            chapter_state_summary="Lily found a signal",
        )
        prompt = provider._build_user_prompt(input_data)
        assert "adventure" in prompt
        assert "courage" in prompt
        assert "科幻小说" in prompt
        assert "延续前文" in prompt

    def test_sends_correct_api_payload(self):
        provider = DashScopeProvider(
            api_key="sk-test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="deepseek-v4-flash",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _mock_api_response()

        with patch("httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)

            provider.generate_chapter(ChapterGenerationInput(target_words=["adventure"]))

            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            payload = call_args[1]["json"]
            assert payload["model"] == "deepseek-v4-flash"
            assert payload["messages"][0]["role"] == "system"
            assert "中国大陆初中生可理解英语水平" in payload["messages"][0]["content"]
            assert payload["messages"][1]["role"] == "user"
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer sk-test-key"

    def test_default_dashscope_model_changes_without_base_url_change(self):
        assert Settings.model_fields["dashscope_model"].default == "deepseek-v4-flash"
        assert (
            Settings.model_fields["dashscope_base_url"].default
            == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    def test_chapter_system_prompt_contains_junior_level_soft_constraint(self):
        assert "中国大陆初中生可理解英语水平" in CHAPTER_GENERATION_SYSTEM_PROMPT

    def test_judge_background_words_filters_false_candidates_and_returns_translations(self):
        provider = DashScopeProvider(
            api_key="sk-test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="deepseek-v4-flash",
        )
        content = json.dumps({
            "words": [
                {"word": "lint", "is_true_out_of_syllabus": True, "translation_cn": "粘毛"},
                {"word": "robot", "is_true_out_of_syllabus": False, "translation_cn": "机器人"},
            ]
        })
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": content}}]}

        with patch("httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)

            result = provider.judge_background_words(
                english_content="The lint stuck to the coat.",
                candidate_words=["lint", "robot", "lint"],
            )

        assert result == {"lint": "粘毛"}
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["model"] == "deepseek-v4-flash"
        assert "lint" in payload["messages"][1]["content"]
        assert provider.call_count == 1

    def test_parse_background_word_judgement_rejects_invalid_shape(self):
        provider = DashScopeProvider(api_key="test-key", base_url="https://fake-api.test")

        with pytest.raises(ValueError, match="words list"):
            provider._parse_background_word_judgement('{"words": {"word": "lint"}}')


class TestCreateLLMProvider:
    def test_returns_dashscope_when_api_key_set(self):
        with patch("app.integrations.llm.dashscope_provider.settings") as mock_settings:
            mock_settings.dashscope_api_key = "sk-test"
            provider = create_llm_provider()
            assert isinstance(provider, DashScopeProvider)

    def test_returns_fake_when_no_api_key(self):
        with patch("app.integrations.llm.dashscope_provider.settings") as mock_settings:
            mock_settings.dashscope_api_key = ""
            provider = create_llm_provider()
            from app.integrations.llm.fake_provider import FakeLLMProvider
            assert isinstance(provider, FakeLLMProvider)
