from app.domain.review.base import QualityReviewContext, QualityReviewResult, tokenize_words


class TargetCoverageRule:
    def evaluate(self, context: QualityReviewContext, result: QualityReviewResult) -> None:
        tokens = tokenize_words(context.english_content)
        hits: dict[str, int] = {}
        missing: list[str] = []

        for target in context.target_words:
            lemma = target.normalized_lemma
            forms = target.normalized_forms
            count = sum(1 for token in tokens if token.normalized in forms)
            hits[lemma] = count
            if count == 0:
                missing.append(lemma)

        result.target_word_hits = hits
        if missing:
            result.fail(f"Missing target words: {', '.join(missing)}.")
