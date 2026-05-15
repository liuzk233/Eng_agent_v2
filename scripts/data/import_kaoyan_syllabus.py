"""Import the Kaoyan English syllabus snapshot into the active syllabus tables.

Usage:
    cd apps/api
    python ../../scripts/data/import_kaoyan_syllabus.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"
DEFAULT_SOURCE_PATH = REPO_ROOT / "data" / "syllabi" / "kaoyan_syllabus.json"

sys.path.insert(0, str(API_ROOT))

from app.models.vocabulary import ExamSyllabus, SyllabusWord  # noqa: E402

SYLLABUS_CODE = "kaoyan"
SYLLABUS_NAME = "Kaoyan English Syllabus"
SOURCE_DESCRIPTION = "Project snapshot: data/syllabi/kaoyan_syllabus.json"


def load_snapshot(path: Path = DEFAULT_SOURCE_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError("Kaoyan syllabus snapshot must be a JSON object")
    return payload


def version_from_snapshot(payload: dict[str, Any]) -> str:
    version = payload.get("version")
    if isinstance(version, str) and version.strip():
        return version.strip()

    created_at = payload.get("created_at")
    if isinstance(created_at, str) and created_at.strip():
        return created_at.split("T", maxsplit=1)[0]

    raise ValueError("Kaoyan syllabus snapshot must include version or created_at")


def normalize_words(payload: dict[str, Any]) -> list[str]:
    raw_words = payload.get("words")
    if not isinstance(raw_words, list):
        raise ValueError("Kaoyan syllabus snapshot must include a words array")

    normalized = {
        word.strip().lower()
        for word in raw_words
        if isinstance(word, str) and word.strip()
    }
    return sorted(normalized)


def import_kaoyan_syllabus(session: Session, source_path: Path = DEFAULT_SOURCE_PATH) -> tuple[ExamSyllabus, int]:
    payload = load_snapshot(source_path)
    version = version_from_snapshot(payload)
    words = normalize_words(payload)

    for syllabus in session.scalars(select(ExamSyllabus)):
        syllabus.is_active = False

    syllabus = session.scalar(
        select(ExamSyllabus).where(
            ExamSyllabus.code == SYLLABUS_CODE,
            ExamSyllabus.version == version,
        )
    )
    if syllabus is None:
        syllabus = ExamSyllabus(
            code=SYLLABUS_CODE,
            name=SYLLABUS_NAME,
            version=version,
            source_description=SOURCE_DESCRIPTION,
            is_active=True,
        )
        session.add(syllabus)
        session.flush()
    else:
        syllabus.name = SYLLABUS_NAME
        syllabus.source_description = SOURCE_DESCRIPTION
        syllabus.is_active = True

    existing_by_lemma = {
        word.lemma: word
        for word in session.scalars(
            select(SyllabusWord).where(SyllabusWord.syllabus_id == syllabus.id)
        )
    }
    source_lemmas = set(words)

    for stale_lemma, stale_word in existing_by_lemma.items():
        if stale_lemma not in source_lemmas:
            session.delete(stale_word)

    for lemma in words:
        word = existing_by_lemma.get(lemma)
        if word is None:
            session.add(
                SyllabusWord(
                    syllabus_id=syllabus.id,
                    lemma=lemma,
                    allowed_forms=[],
                    part_of_speech=None,
                    definition_cn=None,
                )
            )
        else:
            word.allowed_forms = []
            word.part_of_speech = None
            word.definition_cn = None

    session.flush()
    return syllabus, len(words)


def import_with_engine(engine: Engine, source_path: Path = DEFAULT_SOURCE_PATH) -> tuple[str, int]:
    with Session(engine) as session:
        syllabus, count = import_kaoyan_syllabus(session, source_path)
        syllabus_id = str(syllabus.id)
        session.commit()
        return syllabus_id, count


def main() -> None:
    database_url = os.environ.get("VSL_DATABASE_URL")
    if not database_url:
        raise RuntimeError("VSL_DATABASE_URL must be set before importing Kaoyan syllabus")

    engine = create_engine(database_url)
    try:
        syllabus_id, count = import_with_engine(engine)
        print(f"Imported {count} Kaoyan syllabus words into syllabus {syllabus_id}.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
