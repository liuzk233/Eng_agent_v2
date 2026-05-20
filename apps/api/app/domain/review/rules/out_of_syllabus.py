from app.domain.review.base import (
    OutOfSyllabusFinding,
    QualityReviewContext,
    QualityReviewResult,
    normalize_word,
    tokenize_words,
)


class OutOfSyllabusRule:
    def __init__(self, max_rate: float = 0.01) -> None:
        self.max_rate = max_rate

    def evaluate(self, context: QualityReviewContext, result: QualityReviewResult) -> None:
        tokens = tokenize_words(context.english_content)
        allowed_words = self._allowed_words(context)
        findings_by_word: dict[str, OutOfSyllabusFinding] = {}
        reviewed_tokens = []

        for token in tokens:
            if token.normalized in context.normalized_proper_nouns:
                continue
            if self._is_target_word(token.normalized, context):
                continue

            reviewed_tokens.append(token)
            if token.normalized in allowed_words:
                continue

            findings_by_word.setdefault(
                token.normalized,
                OutOfSyllabusFinding(
                    word=token.normalized,
                    translation_cn=self._translation_for(token.normalized, context.glosses),
                ),
            )

        total_words = len(reviewed_tokens)
        out_of_syllabus_count = sum(1 for token in reviewed_tokens if token.normalized in findings_by_word)
        result.out_of_syllabus_words = list(findings_by_word.values())
        result.out_of_syllabus_rate = out_of_syllabus_count / total_words if total_words else 0
        if result.out_of_syllabus_rate > self.max_rate:
            result.add_note(
                f"Out-of-syllabus candidate rate {result.out_of_syllabus_rate:.2%} exceeds {self.max_rate:.2%}."
            )

    def _allowed_words(self, context: QualityReviewContext) -> set[str]:
        allowed = set(context.normalized_syllabus_lemmas)
        allowed.update(context.normalized_syllabus_forms)
        for forms in context.target_forms_by_lemma.values():
            allowed.update(forms)
        return allowed

    def _is_target_word(self, word: str, context: QualityReviewContext) -> bool:
        return any(word in forms for forms in context.target_forms_by_lemma.values())

    def _translation_for(self, word: str, glosses: dict[str, str]) -> str:
        return glosses.get(word) or glosses.get(normalize_word(word)) or "待标注"
