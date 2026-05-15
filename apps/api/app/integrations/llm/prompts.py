from app.domain.enums import StoryStyle

STYLE_NAMES: dict[StoryStyle, str] = {
    StoryStyle.web_novel: "网络爽文",
    StoryStyle.science_fiction: "科幻小说",
    StoryStyle.exam_reading: "应试阅读文章",
}

CHAPTER_GENERATION_SYSTEM_PROMPT = (
    "你是一位英语故事创作专家。根据用户提供的目标词和故事上下文，"
    "生成一篇连贯的英语故事章节。\n\n"
    "输出要求：\n"
    "1. 英文正文：目标词用 **加粗** 标记\n"
    "2. 目标词必须全部自然融入正文\n"
    "3. 正文长度 300-500 词\n"
    "4. 附带完整中文翻译\n\n"
    "输出格式（严格 JSON）：\n"
    '{"english_content": "...", "highlighted_target_words": ["word1", "word2"], '
    '"chinese_translation": "..."}'
)


def build_chapter_user_prompt(
    target_words: list[str],
    style: StoryStyle,
    chapter_number: int,
    target_chapter_count: int,
    story_bible_summary: str = "",
    previous_chapter_summary: str = "",
) -> str:
    parts = [
        f"风格：{STYLE_NAMES.get(style, style.value)}",
        f"章节：第 {chapter_number} 章 / 共 {target_chapter_count} 章",
        f"目标词：{', '.join(target_words)}",
    ]
    if story_bible_summary:
        parts.append(f"故事设定：{story_bible_summary}")
    if previous_chapter_summary:
        parts.append(f"上一章摘要：{previous_chapter_summary}")
    if chapter_number == 1:
        parts.append("这是第一章，请开头引入故事和角色。")
    else:
        parts.append("请延续前文剧情，保持角色和世界观一致。")
    return "\n".join(parts)
