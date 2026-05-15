from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol


WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


@dataclass(frozen=True)
class TargetWord:
    lemma: str
    allowed_forms: set[str] = field(default_factory=set)

    @property
    def normalized_lemma(self) -> str:
        return normalize_word(self.lemma)

    @property
    def normalized_forms(self) -> set[str]:
        return {normalize_word(form) for form in self.allowed_forms} | {self.normalized_lemma}


@dataclass(frozen=True)
class QualityReviewContext:
    english_content: str
    target_words: list[TargetWord] = field(default_factory=list)
    syllabus_lemmas: set[str] = field(default_factory=set)
    syllabus_allowed_forms: dict[str, set[str]] = field(default_factory=dict)
    proper_nouns: set[str] = field(default_factory=set)
    glosses: dict[str, str] = field(default_factory=dict)

    @property
    def normalized_syllabus_lemmas(self) -> set[str]:
        return {normalize_word(word) for word in self.syllabus_lemmas}

    @property
    def normalized_syllabus_forms(self) -> set[str]:
        forms: set[str] = set()
        for lemma, allowed_forms in self.syllabus_allowed_forms.items():
            forms.add(normalize_word(lemma))
            forms.update(normalize_word(form) for form in allowed_forms)
        return forms

    @property
    def normalized_proper_nouns(self) -> set[str]:
        return {normalize_word(word) for word in self.proper_nouns}

    @property
    def target_forms_by_lemma(self) -> dict[str, set[str]]:
        return {target.normalized_lemma: target.normalized_forms for target in self.target_words}


@dataclass(frozen=True)
class WordToken:
    original: str
    normalized: str


@dataclass(frozen=True)
class OutOfSyllabusFinding:
    word: str
    translation_cn: str


@dataclass
class QualityReviewResult:
    word_count: int = 0
    target_word_hits: dict[str, int] = field(default_factory=dict)
    out_of_syllabus_rate: float = 0
    out_of_syllabus_words: list[OutOfSyllabusFinding] = field(default_factory=list)
    passed: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def review_notes(self) -> str | None:
        if not self.notes:
            return None
        return "\n".join(self.notes)

    def fail(self, note: str) -> None:
        self.passed = False
        self.notes.append(note)

    def add_note(self, note: str) -> None:
        self.notes.append(note)


class QualityRule(Protocol):
    def evaluate(self, context: QualityReviewContext, result: QualityReviewResult) -> None:
        ...


def run_quality_rules(context: QualityReviewContext, rules: list[QualityRule]) -> QualityReviewResult:
    result = QualityReviewResult(word_count=len(tokenize_words(context.english_content)))
    for rule in rules:
        rule.evaluate(context, result)
    return result


def tokenize_words(text: str) -> list[WordToken]:
    return [WordToken(match.group(0), normalize_word(match.group(0))) for match in WORD_PATTERN.finditer(text)]


def normalize_word(word: str) -> str:
    lowered = word.strip("'").lower()
    if lowered.endswith("'s"):
        lowered = lowered[:-2]
    return lemmatize_simple(lowered)


def lemmatize_simple(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return f"{word[:-3]}y"
    if len(word) > 4 and word.endswith("ied"):
        return f"{word[:-3]}y"
    if len(word) > 5 and word.endswith("ing"):
        stem = word[:-3]
        return undouble_final_consonant(stem)
    if len(word) > 4 and word.endswith("ed"):
        stem = word[:-2]
        if stem.endswith("i"):
            return f"{stem[:-1]}y"
        return undouble_final_consonant(stem)
    if len(word) > 3 and word.endswith("es"):
        if word.endswith(("ches", "shes", "sses", "xes", "zes")):
            return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def undouble_final_consonant(stem: str) -> str:
    if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in {"a", "e", "i", "o", "u"}:
        return stem[:-1]
    return stem
