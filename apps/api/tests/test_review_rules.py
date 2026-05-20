from app.domain.review.base import QualityReviewContext, TargetWord, run_quality_rules
from app.domain.review.rules.length import LengthRule
from app.domain.review.rules.out_of_syllabus import OutOfSyllabusRule
from app.domain.review.rules.target_coverage import TargetCoverageRule


def test_target_coverage_counts_lemma_and_allowed_forms() -> None:
    context = QualityReviewContext(
        english_content="Mina achieved the goal and will achieve another one.",
        target_words=[
            TargetWord(lemma="achieve", allowed_forms={"achieved"}),
            TargetWord(lemma="curious"),
        ],
    )

    report = run_quality_rules(context, [TargetCoverageRule()])

    assert report.target_word_hits == {"achieve": 2, "curious": 0}
    assert report.passed is False
    assert "Missing target words: curious" in report.review_notes


def test_out_of_syllabus_rule_exempts_targets_forms_and_proper_nouns() -> None:
    context = QualityReviewContext(
        english_content="Lina achieved clear progress on Mars with zephyr.",
        target_words=[TargetWord(lemma="achieve", allowed_forms={"achieved"})],
        syllabus_lemmas={"clear", "progress", "on", "with"},
        proper_nouns={"Lina", "Mars"},
        glosses={"zephyr": "西风"},
    )

    report = run_quality_rules(context, [OutOfSyllabusRule(max_rate=0.2)])

    assert report.out_of_syllabus_rate == 1 / 5
    assert [(word.word, word.translation_cn) for word in report.out_of_syllabus_words] == [("zephyr", "西风")]
    assert report.passed is True


def test_out_of_syllabus_rule_collects_candidates_without_failing_when_rate_exceeds_one_percent() -> None:
    allowed_words = ["plain"] * 98
    content = " ".join([*allowed_words, "xenolith", "quasar"])
    context = QualityReviewContext(
        english_content=content,
        syllabus_lemmas={"plain"},
        glosses={"xenolith": "捕虏岩", "quasar": "类星体"},
    )

    report = run_quality_rules(context, [OutOfSyllabusRule(max_rate=0.01)])

    assert report.out_of_syllabus_rate == 0.02
    assert {word.word for word in report.out_of_syllabus_words} == {"xenolith", "quasar"}
    assert report.passed is True
    assert "Out-of-syllabus candidate rate 2.00% exceeds 1.00%." in report.review_notes


def test_length_rule_accepts_three_hundred_to_five_hundred_words() -> None:
    context = QualityReviewContext(english_content=" ".join(["word"] * 300))

    report = run_quality_rules(context, [LengthRule(min_words=300, max_words=500)])

    assert report.word_count == 300
    assert report.passed is True


def test_length_rule_rejects_short_or_long_chapters() -> None:
    short = QualityReviewContext(english_content=" ".join(["word"] * 299))
    long = QualityReviewContext(english_content=" ".join(["word"] * 501))

    short_report = run_quality_rules(short, [LengthRule(min_words=300, max_words=500)])
    long_report = run_quality_rules(long, [LengthRule(min_words=300, max_words=500)])

    assert short_report.passed is False
    assert long_report.passed is False
    assert "Expected 300-500 words, got 299" in short_report.review_notes
    assert "Expected 300-500 words, got 501" in long_report.review_notes
