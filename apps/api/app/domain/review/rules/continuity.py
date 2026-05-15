from app.domain.review.base import (
    QualityReviewContext,
    QualityReviewResult,
    QualityRule,
)


class ContinuityRule:
    def __init__(
        self,
        *,
        story_bible_characters: dict | None = None,
        story_bible_immutable_facts: dict | None = None,
        previous_chapter_summary: str | None = None,
        previous_unresolved_hooks: list | None = None,
    ) -> None:
        self.story_bible_characters = story_bible_characters or {}
        self.story_bible_immutable_facts = story_bible_immutable_facts or {}
        self.previous_chapter_summary = previous_chapter_summary
        self.previous_unresolved_hooks = previous_unresolved_hooks or []

    def evaluate(self, context: QualityReviewContext, result: QualityReviewResult) -> None:
        if not self.previous_chapter_summary and not self.story_bible_characters:
            result.add_note("ContinuityRule: first chapter, no continuity requirements")
            return

        missing_characters = self._find_missing_characters(context.english_content)
        violated_facts = self._find_violated_facts(context.english_content)

        if missing_characters:
            result.fail(
                f"ContinuityRule: main characters missing from content: "
                f"{', '.join(missing_characters)}"
            )

        if violated_facts:
            result.fail(
                f"ContinuityRule: immutable facts appear violated: "
                f"{', '.join(violated_facts)}"
            )

    def _find_missing_characters(self, english_content: str) -> list[str]:
        content_lower = english_content.lower()
        missing: list[str] = []
        for char_name in self.story_bible_characters:
            if char_name.lower() not in content_lower:
                missing.append(char_name)
        return missing

    def _find_violated_facts(self, english_content: str) -> list[str]:
        content_lower = english_content.lower()
        violated: list[str] = []
        for fact_key, fact_value in self.story_bible_immutable_facts.items():
            if isinstance(fact_value, str) and fact_value.lower() not in content_lower:
                continue
        return violated
