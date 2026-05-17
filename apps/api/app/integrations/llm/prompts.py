from app.domain.enums import StoryStyle

STYLE_NAMES: dict[StoryStyle, str] = {
    StoryStyle.web_novel: "网络爽文",
    StoryStyle.science_fiction: "科幻小说",
    StoryStyle.exam_reading: "应试阅读文章",
}

WEB_NOVEL_FEW_SHOT_GUIDE = """\
网络爽文风格规则：
- 这不是普通儿童探险或平铺直叙的村庄发现故事；必须有明确对抗、危机、选择和局势反转。
- 章节前 80 个英文词内必须出现压迫感开场和外部阻力，例如被质疑、被追赶、被封锁、被夺走机会。
- 使用短句推进。多用 6-14 个词的句子制造节奏，不要连续写解释性长段。
- 正文必须包含冲突升级、反转爆发和结尾钩子，至少 3 个节奏信号要清晰可见。
- 爽点来自人物选择和局势反转，不模仿任何具体作品、作者、角色或世界观。
- 英文正文仍保持清晰自然，目标词必须自然出现并用 **bold** 标记。
- 不要为了覆盖目标词而硬塞错误词性；如果目标词是名词，就按名词使用，如果是形容词，就修饰合适名词。
- 不要复制示例人物名、场景、样例目标词或句子；只学习节奏结构。

硬性结构：
1. Opening pressure: 第一段直接给危机，不要从平静日常开始。
2. Short push: 用短句连续推进行动。
3. Escalation: 让阻力变强，主角付出代价或失去选择。
4. Reversal: 主角做出选择后，局势突然翻转。
5. Hook: 结尾留下新的威胁、秘密或未完成承诺。

原创网文 few-shot：
Example A:
English: The hall fell silent. Everyone expected Mira to step back, but she raised the broken badge and made a calm **decision**.
Chinese: 大厅骤然安静。所有人都以为米拉会退缩，可她举起破碎徽章，平静地做出了决定。
Rhythm: 压迫感开场 -> 短句推进 -> 反转爆发。

Example B:
English: Rain hit the old gate. Ken had only one **chance** left. When the guard laughed, the hidden mark on his wrist began to shine.
Chinese: 雨点砸在旧门上。肯只剩最后一次机会。守卫发笑时，他腕上的暗纹忽然亮起。
Rhythm: 冲突升级 -> 情绪蓄力 -> 结尾钩子。
"""

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
    if style == StoryStyle.web_novel:
        parts.append(WEB_NOVEL_FEW_SHOT_GUIDE)
    return "\n".join(parts)
