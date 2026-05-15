from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


def table(name: str):
    return Base.metadata.tables[name]


def column_names(name: str) -> set[str]:
    return set(table(name).columns.keys())


def foreign_key_targets(name: str) -> set[str]:
    targets: set[str] = set()
    for column in table(name).columns:
        for foreign_key in column.foreign_keys:
            targets.add(str(foreign_key.column))
    return targets


def unique_column_sets(name: str) -> set[tuple[str, ...]]:
    return {
        tuple(constraint.columns.keys())
        for constraint in table(name).constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_metadata_contains_design_tables() -> None:
    assert set(Base.metadata.tables.keys()) == {
        "users",
        "invite_codes",
        "story_projects",
        "chapters",
        "story_bibles",
        "chapter_states",
        "chapter_target_words",
        "generation_tasks",
        "quality_reports",
        "exam_syllabi",
        "syllabus_words",
        "learning_progress",
    }


def test_auth_schema_matches_closed_beta_requirements() -> None:
    assert column_names("users") >= {
        "id",
        "email",
        "password_hash",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert isinstance(table("users").c.id.type, UUID)
    assert isinstance(table("users").c.email.type, String)
    assert isinstance(table("users").c.password_hash.type, String)
    assert isinstance(table("users").c.is_active.type, Boolean)
    assert ("email",) in unique_column_sets("users")

    assert column_names("invite_codes") >= {
        "id",
        "code_hash",
        "max_uses",
        "used_count",
        "expires_at",
        "created_by_user_id",
        "created_at",
    }
    assert "users.id" in foreign_key_targets("invite_codes")
    assert ("code_hash",) in unique_column_sets("invite_codes")


def test_story_and_continuity_tables_match_design() -> None:
    assert column_names("story_projects") >= {
        "id",
        "user_id",
        "title",
        "style",
        "target_chapter_count",
        "current_chapter_number",
        "created_at",
        "updated_at",
    }
    assert "users.id" in foreign_key_targets("story_projects")

    assert column_names("chapters") >= {
        "id",
        "story_project_id",
        "chapter_number",
        "status",
        "english_content",
        "chinese_translation",
        "word_count",
        "created_at",
        "updated_at",
    }
    assert "story_projects.id" in foreign_key_targets("chapters")
    assert ("story_project_id", "chapter_number") in unique_column_sets("chapters")

    assert column_names("story_bibles") >= {
        "id",
        "story_project_id",
        "characters",
        "worldview",
        "main_plot",
        "tone",
        "immutable_facts",
        "created_at",
        "updated_at",
    }
    assert isinstance(table("story_bibles").c.characters.type, JSON)
    assert "story_projects.id" in foreign_key_targets("story_bibles")
    assert ("story_project_id",) in unique_column_sets("story_bibles")

    assert column_names("chapter_states") >= {
        "id",
        "chapter_id",
        "summary",
        "unresolved_hooks",
        "character_states",
        "continuity_constraints",
        "created_at",
        "updated_at",
    }
    assert isinstance(table("chapter_states").c.unresolved_hooks.type, JSON)
    assert "chapters.id" in foreign_key_targets("chapter_states")
    assert ("chapter_id",) in unique_column_sets("chapter_states")


def test_vocabulary_and_progress_tables_match_design() -> None:
    assert column_names("exam_syllabi") >= {
        "id",
        "code",
        "name",
        "version",
        "source_description",
        "is_active",
        "created_at",
    }
    assert ("code", "version") in unique_column_sets("exam_syllabi")

    assert column_names("syllabus_words") >= {
        "id",
        "syllabus_id",
        "lemma",
        "allowed_forms",
        "part_of_speech",
        "definition_cn",
        "created_at",
    }
    assert "exam_syllabi.id" in foreign_key_targets("syllabus_words")
    assert isinstance(table("syllabus_words").c.allowed_forms.type, JSON)
    assert ("syllabus_id", "lemma") in unique_column_sets("syllabus_words")

    assert column_names("chapter_target_words") >= {
        "id",
        "chapter_id",
        "word",
        "lemma",
        "source",
        "position",
        "created_at",
    }
    assert "chapters.id" in foreign_key_targets("chapter_target_words")
    assert ("chapter_id", "lemma") in unique_column_sets("chapter_target_words")

    assert column_names("learning_progress") >= {
        "id",
        "user_id",
        "lemma",
        "encounter_count",
        "last_seen_chapter_id",
        "created_at",
        "updated_at",
    }
    assert "users.id" in foreign_key_targets("learning_progress")
    assert "chapters.id" in foreign_key_targets("learning_progress")
    assert ("user_id", "lemma") in unique_column_sets("learning_progress")


def test_generation_and_quality_report_tables_match_review_loop() -> None:
    assert column_names("generation_tasks") >= {
        "id",
        "chapter_id",
        "status",
        "retry_count",
        "fallback_reason",
        "provider_name",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    }
    assert "chapters.id" in foreign_key_targets("generation_tasks")
    assert isinstance(table("generation_tasks").c.retry_count.type, Integer)

    assert column_names("quality_reports") >= {
        "id",
        "generation_task_id",
        "chapter_id",
        "out_of_syllabus_rate",
        "out_of_syllabus_words",
        "target_word_hits",
        "review_notes",
        "passed",
        "created_at",
    }
    assert "generation_tasks.id" in foreign_key_targets("quality_reports")
    assert "chapters.id" in foreign_key_targets("quality_reports")
    assert isinstance(table("quality_reports").c.out_of_syllabus_words.type, JSON)
    assert isinstance(table("quality_reports").c.review_notes.type, Text)
    assert isinstance(table("quality_reports").c.created_at.type, DateTime)


def test_initial_alembic_revision_is_traceable() -> None:
    migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "0001_initial_schema.py"
    spec = spec_from_file_location("initial_schema_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "0001_initial_schema"
    assert migration.down_revision is None
    assert callable(migration.upgrade)
    assert callable(migration.downgrade)
