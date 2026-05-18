from __future__ import annotations

import json
import logging

import httpx

from app.core.config import settings
from app.domain.enums import StoryStyle
from app.integrations.llm.base import (
    ChapterGenerationInput,
    ChapterGenerationOutput,
    LLMProvider,
    RetryConfig,
    UsageRecord,
)
from app.integrations.llm.prompts import (
    CHAPTER_GENERATION_SYSTEM_PROMPT,
    STYLE_NAMES,
    build_chapter_user_prompt,
)

logger = logging.getLogger(__name__)

_DASHSCOPE_CHAT_URL = "/chat/completions"


class DashScopeProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key or settings.dashscope_api_key
        self.base_url = (base_url or settings.dashscope_base_url).rstrip("/")
        self.model = model or settings.dashscope_model
        self.timeout = timeout
        self.call_count = 0

    def generate_chapter(
        self,
        input_data: ChapterGenerationInput,
        retry_config: RetryConfig | None = None,
    ) -> tuple[ChapterGenerationOutput, UsageRecord]:
        self.call_count += 1

        system_prompt = CHAPTER_GENERATION_SYSTEM_PROMPT
        user_prompt = self._build_user_prompt(input_data)

        response_body = self._call_api(system_prompt, user_prompt)
        content = response_body["choices"][0]["message"]["content"]

        output = self._parse_output(content, input_data.target_words)
        usage = self._extract_usage(response_body)

        return output, usage

    def _call_api(self, system_prompt: str, user_prompt: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}{_DASHSCOPE_CHAT_URL}"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error(
                "DashScope API error: status=%d body=%s",
                response.status_code,
                response.text[:500],
            )
            raise RuntimeError(
                f"DashScope API returned status {response.status_code}: {response.text[:200]}"
            )

        return response.json()

    def _build_user_prompt(self, input_data: ChapterGenerationInput) -> str:
        story_bible_summary = ""
        if input_data.story_bible_main_plot:
            parts = []
            if input_data.story_bible_characters:
                char_desc = ", ".join(
                    f"{name}({desc})" for name, desc in input_data.story_bible_characters.items()
                )
                parts.append(f"角色: {char_desc}")
            parts.append(f"世界观: {input_data.story_bible_worldview or ''}")
            parts.append(f"主线: {input_data.story_bible_main_plot}")
            story_bible_summary = "; ".join(parts)

        previous_summary = input_data.chapter_state_summary
        chapter_outline = input_data.story_bible_immutable_facts.get("chapter_outline") if input_data.story_bible_immutable_facts else None

        return build_chapter_user_prompt(
            target_words=input_data.target_words,
            style=input_data.style,
            chapter_number=input_data.chapter_number,
            target_chapter_count=input_data.target_chapter_count,
            story_bible_summary=story_bible_summary,
            previous_chapter_summary=previous_summary or "",
            chapter_outline=chapter_outline,
        )

    def _parse_output(
        self, content: str, target_words: list[str]
    ) -> ChapterGenerationOutput:
        # Try JSON parse first
        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # skip ```json
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            parsed = json.loads(text)
            return ChapterGenerationOutput(
                english_content=parsed.get("english_content", ""),
                highlighted_target_words=parsed.get("highlighted_target_words", target_words),
                chinese_translation=parsed.get("chinese_translation", ""),
            )
        except json.JSONDecodeError:
            logger.warning("DashScope output is not valid JSON, extracting raw content")
            # Fallback: treat entire content as english_content
            return ChapterGenerationOutput(
                english_content=text,
                highlighted_target_words=target_words,
                chinese_translation="",
            )

    def _extract_usage(self, body: dict) -> UsageRecord:
        usage = body.get("usage", {})
        return UsageRecord(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            model_name=self.model,
        )


def create_llm_provider() -> LLMProvider:
    if settings.dashscope_api_key:
        return DashScopeProvider()
    logger.info("No DASHSCOPE_API_KEY configured, using FakeLLMProvider")
    from app.integrations.llm.fake_provider import FakeLLMProvider

    return FakeLLMProvider()
