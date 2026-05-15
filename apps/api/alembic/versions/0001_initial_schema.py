"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-11 19:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_pk() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False)


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    from alembic import op

    op.create_table(
        "users",
        uuid_pk(),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "invite_codes",
        uuid_pk(),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_invite_codes_code_hash", "invite_codes", ["code_hash"])
    op.create_index("ix_invite_codes_created_by_user_id", "invite_codes", ["created_by_user_id"])

    op.create_table(
        "exam_syllabi",
        uuid_pk(),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("source_description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", "version"),
    )

    op.create_table(
        "story_projects",
        uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("style", sa.String(length=32), nullable=False),
        sa.Column("target_chapter_count", sa.Integer(), nullable=False),
        sa.Column("current_chapter_number", sa.Integer(), nullable=False, server_default="1"),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_story_projects_user_id", "story_projects", ["user_id"])

    op.create_table(
        "syllabus_words",
        uuid_pk(),
        sa.Column("syllabus_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lemma", sa.String(length=120), nullable=False),
        sa.Column("allowed_forms", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("part_of_speech", sa.String(length=64), nullable=True),
        sa.Column("definition_cn", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["syllabus_id"], ["exam_syllabi.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("syllabus_id", "lemma"),
    )
    op.create_index("ix_syllabus_words_syllabus_id", "syllabus_words", ["syllabus_id"])
    op.create_index("ix_syllabus_words_lemma", "syllabus_words", ["lemma"])

    op.create_table(
        "chapters",
        uuid_pk(),
        sa.Column("story_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("english_content", sa.Text(), nullable=True),
        sa.Column("chinese_translation", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["story_project_id"], ["story_projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("story_project_id", "chapter_number"),
    )
    op.create_index("ix_chapters_story_project_id", "chapters", ["story_project_id"])

    op.create_table(
        "story_bibles",
        uuid_pk(),
        sa.Column("story_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("characters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("worldview", sa.Text(), nullable=True),
        sa.Column("main_plot", sa.Text(), nullable=True),
        sa.Column("tone", sa.Text(), nullable=True),
        sa.Column("immutable_facts", sa.JSON(), nullable=False, server_default="{}"),
        *timestamps(),
        sa.ForeignKeyConstraint(["story_project_id"], ["story_projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("story_project_id"),
    )
    op.create_index("ix_story_bibles_story_project_id", "story_bibles", ["story_project_id"])

    op.create_table(
        "chapter_states",
        uuid_pk(),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("unresolved_hooks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("character_states", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("continuity_constraints", sa.JSON(), nullable=False, server_default="{}"),
        *timestamps(),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("chapter_id"),
    )
    op.create_index("ix_chapter_states_chapter_id", "chapter_states", ["chapter_id"])

    op.create_table(
        "chapter_target_words",
        uuid_pk(),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("word", sa.String(length=120), nullable=False),
        sa.Column("lemma", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("chapter_id", "lemma"),
    )
    op.create_index("ix_chapter_target_words_chapter_id", "chapter_target_words", ["chapter_id"])
    op.create_index("ix_chapter_target_words_lemma", "chapter_target_words", ["lemma"])

    op.create_table(
        "generation_tasks",
        uuid_pk(),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_reason", sa.Text(), nullable=True),
        sa.Column("provider_name", sa.String(length=80), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_generation_tasks_status", "generation_tasks", ["status"])
    op.create_index("ix_generation_tasks_chapter_id", "generation_tasks", ["chapter_id"])

    op.create_table(
        "learning_progress",
        uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lemma", sa.String(length=120), nullable=False),
        sa.Column("encounter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["last_seen_chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "lemma"),
    )
    op.create_index("ix_learning_progress_user_id", "learning_progress", ["user_id"])
    op.create_index("ix_learning_progress_lemma", "learning_progress", ["lemma"])
    op.create_index("ix_learning_progress_last_seen_chapter_id", "learning_progress", ["last_seen_chapter_id"])

    op.create_table(
        "quality_reports",
        uuid_pk(),
        sa.Column("generation_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("out_of_syllabus_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("out_of_syllabus_words", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("target_word_hits", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generation_task_id"], ["generation_tasks.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_quality_reports_generation_task_id", "quality_reports", ["generation_task_id"])
    op.create_index("ix_quality_reports_chapter_id", "quality_reports", ["chapter_id"])


def downgrade() -> None:
    from alembic import op

    op.drop_index("ix_quality_reports_chapter_id", table_name="quality_reports")
    op.drop_index("ix_quality_reports_generation_task_id", table_name="quality_reports")
    op.drop_table("quality_reports")
    op.drop_index("ix_learning_progress_last_seen_chapter_id", table_name="learning_progress")
    op.drop_index("ix_learning_progress_lemma", table_name="learning_progress")
    op.drop_index("ix_learning_progress_user_id", table_name="learning_progress")
    op.drop_table("learning_progress")
    op.drop_index("ix_generation_tasks_chapter_id", table_name="generation_tasks")
    op.drop_index("ix_generation_tasks_status", table_name="generation_tasks")
    op.drop_table("generation_tasks")
    op.drop_index("ix_chapter_target_words_lemma", table_name="chapter_target_words")
    op.drop_index("ix_chapter_target_words_chapter_id", table_name="chapter_target_words")
    op.drop_table("chapter_target_words")
    op.drop_index("ix_chapter_states_chapter_id", table_name="chapter_states")
    op.drop_table("chapter_states")
    op.drop_index("ix_story_bibles_story_project_id", table_name="story_bibles")
    op.drop_table("story_bibles")
    op.drop_index("ix_chapters_story_project_id", table_name="chapters")
    op.drop_table("chapters")
    op.drop_index("ix_syllabus_words_lemma", table_name="syllabus_words")
    op.drop_index("ix_syllabus_words_syllabus_id", table_name="syllabus_words")
    op.drop_table("syllabus_words")
    op.drop_index("ix_story_projects_user_id", table_name="story_projects")
    op.drop_table("story_projects")
    op.drop_table("exam_syllabi")
    op.drop_index("ix_invite_codes_created_by_user_id", table_name="invite_codes")
    op.drop_index("ix_invite_codes_code_hash", table_name="invite_codes")
    op.drop_table("invite_codes")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
