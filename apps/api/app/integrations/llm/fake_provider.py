from __future__ import annotations

from app.domain.enums import StoryStyle
from app.integrations.llm.base import (
    ChapterGenerationInput,
    ChapterGenerationOutput,
    LLMProvider,
    RetryConfig,
    UsageRecord,
)

_FAKE_ENGLISH_TEMPLATE = (
    "In a quiet village, a young student named Lily discovered an ancient book. "
    "The book contained mysterious **{word0}** that seemed to glow in the dark. "
    "She showed it to her friend Tom, who was known for his **{word1}** nature. "
    "\"We should investigate this,\" Tom said with great **{word2}**. "
    "They decided to visit the old library, where the librarian, Mrs. Chen, "
    "had a reputation for her **{word3}** knowledge of local history. "
    "She examined the book carefully and nodded. "
    "\"This is indeed **{word4}**,\" she whispered. "
    "The pages revealed a **{word5}** map leading to a hidden garden. "
    "Lily felt a sense of **{word6}** as they followed the path described. "
    "Along the way, they encountered **{word7}** flowers that had never been documented. "
    "Tom took careful notes, showing his usual **{word8}** attention to detail. "
    "At the end of the path, they found a **{word9}** tree with golden leaves, "
    "standing as a testament to the village’s forgotten past. "
    "Lily and Tom sat beneath the tree and read the ancient book together. "
    "The words on the pages seemed to shift and rearrange themselves, "
    "forming new sentences that told of a long-lost civilization. "
    "Tom pointed out that the book mentioned several important historical events "
    "that had been forgotten by the modern world. "
    "Lily realized that this discovery could change everything they knew about their village. "
    "She carefully copied the most important passages into her notebook, "
    "making sure to preserve every detail. "
    "As the sun began to set, they decided to return the next day to continue their research. "
    "The journey home was filled with excited conversation about what they had found. "
    "Mrs. Chen had told them that the tree was said to be over a thousand years old, "
    "planted by the founders of the village as a symbol of hope and knowledge. "
    "Lily could not wait to share her discovery with the rest of the village."
)

_FAKE_CHINESE_TEMPLATE = (
    "在一个宁静的村庄里，"
    "一个名叫Lily的年轻学生发现了一本古书。"
    "书中包含神秘的{word0_cn}，似乎在黑暗中发光。"
    "她把它展示给以{word1_cn}性格闻名的朋友Tom。"
    "\"我们应该调查这件事，\""
    "Tom带着极大的{word2_cn}说道。"
    "他们决定去旧图书馆，"
    "管理员陈太太以对当地历史的{word3_cn}知识而闻名。"
    "她仔细检查了这本书并点了点头。"
    "\"这确实是{word4_cn}，\"她低声说。"
    "书页揭示了一张通往隐藏花园的{word5_cn}地图。"
    "Lily在沿着描述的路径行进时感到了一种{word6_cn}。"
    "在途中，他们遇到了从未被记录过的{word7_cn}花朵。"
    "Tom做了详细的笔记，"
    "展现了他一如既往的{word8_cn}对细节的关注。"
    "在路的尽头，他们发现了一棵{word9_cn}的金叶树，"
    "作为村庄被遗忘的过去的见证。"
    "Lily和Tom坐在树下，一起阅读了这本古书。"
    "书页上的文字似乎在移动和重新排列，"
    "形成了讲述一个失落文明的新句子。"
    "Tom指出书中提到了几个重要的历史事件，"
    "这些事件已被现代世界遗忘。"
    "Lily意识到这一发现可能改变他们对村庄的一切认知。"
    "她仔细地将最重要的段落抄写到笔记本上，"
    "确保保留每一个细节。"
    "当太阳开始西沉时，他们决定第二天再来继续研究。"
    "回家的路上充满了关于他们所发现之事的热烈讨论。"
    "陈太太告诉他们这棵树据说已有一千多年的历史，"
    "由村庄的建立者种植，作为希望和知识的象征。"
    "Lily迫不及待地想与村庄里的其他人分享她的发现。"
)

_WORD_CN_MAP: dict[str, str] = {
    "adventure": "冒险",
    "curious": "好奇的",
    "enthusiasm": "热情",
    "remarkable": "非凡的",
    "mysterious": "神秘的",
    "ancient": "古老的",
    "excitement": "兴奋",
    "beautiful": "美丽的",
    "diligent": "勤勉的",
    "extraordinary": "非凡的",
    "courage": "勇气",
    "determine": "决心",
    "explore": "探索",
    "fortune": "运气",
    "generous": "慷慨的",
    "harmony": "和谐",
    "inspire": "激励",
    "journey": "旅程",
    "knowledge": "知识",
    "library": "图书馆",
}


class FakeLLMProvider(LLMProvider):
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.call_count = 0

    def generate_chapter(
        self,
        input_data: ChapterGenerationInput,
        retry_config: RetryConfig | None = None,
    ) -> tuple[ChapterGenerationOutput, UsageRecord]:
        if self.should_fail:
            raise RuntimeError("FakeLLMProvider configured to fail")

        self.call_count += 1
        output = self._build_output(input_data)
        usage = UsageRecord(
            prompt_tokens=100,
            completion_tokens=300,
            total_tokens=400,
            model_name="fake-provider-v1",
        )
        return output, usage

    def _build_output(self, input_data: ChapterGenerationInput) -> ChapterGenerationOutput:
        words = input_data.target_words
        padded = list(words) + [
            "adventure", "curious", "enthusiasm", "remarkable",
            "mysterious", "ancient", "excitement", "beautiful",
            "diligent", "extraordinary",
        ][:max(0, 10 - len(words))]

        english = _FAKE_ENGLISH_TEMPLATE
        for i, word in enumerate(padded[:10]):
            english = english.replace(f"{{word{i}}}", word)

        chinese = _FAKE_CHINESE_TEMPLATE
        for i, word in enumerate(padded[:10]):
            cn = _WORD_CN_MAP.get(word, word)
            chinese = chinese.replace(f"{{word{i}_cn}}", cn)

        highlighted = list(words)

        if input_data.style == StoryStyle.exam_reading:
            english = english.replace("In a quiet village", "In modern society")
            english = english.replace("ancient book", "research paper")

        return ChapterGenerationOutput(
            english_content=english,
            highlighted_target_words=highlighted,
            chinese_translation=chinese,
        )
