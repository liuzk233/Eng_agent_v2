from app.domain.review.base import QualityReviewContext, QualityReviewResult


class LengthRule:
    def __init__(self, min_words: int = 300, max_words: int = 500) -> None:
        self.min_words = min_words
        self.max_words = max_words

    def evaluate(self, context: QualityReviewContext, result: QualityReviewResult) -> None:
        if self.min_words <= result.word_count <= self.max_words:
            return

        result.fail(f"Expected {self.min_words}-{self.max_words} words, got {result.word_count}.")
