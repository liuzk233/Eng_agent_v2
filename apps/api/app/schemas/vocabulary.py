from pydantic import BaseModel, Field, root_validator, validator

from app.domain.enums import TargetWordSource


class TargetWordInput(BaseModel):
    word: str = Field(min_length=1, max_length=120)
    source: TargetWordSource
    lemma: str | None = None

    @validator("word")
    @classmethod
    def normalize_word(cls, word: str) -> str:
        clean = word.strip()
        if not clean:
            raise ValueError("word cannot be blank")
        return clean

    @root_validator(skip_on_failure=True)
    def default_lemma(cls, values: dict) -> dict:
        word = values.get("word", "")
        lemma = values.get("lemma")
        if lemma is None:
            values["lemma"] = word.strip().lower()
        else:
            values["lemma"] = lemma.strip().lower()
        if not values["lemma"]:
            raise ValueError("lemma cannot be blank")
        return values


class TargetWordsSubmitRequest(BaseModel):
    words: list[TargetWordInput] = Field(min_items=1, max_items=10)

    @root_validator(skip_on_failure=True)
    def dedupe_by_lemma(cls, values: dict) -> dict:
        deduped: list[TargetWordInput] = []
        seen: set[str] = set()
        for word in values.get("words") or []:
            if word.lemma not in seen:
                deduped.append(word)
                seen.add(word.lemma)
        values["words"] = deduped
        return values
