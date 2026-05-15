"""Seed demo data for UAT testing.

Usage:
    cd apps/api
    python ../../scripts/uat/seed_demo_data.py
"""
from __future__ import annotations

import os
import secrets
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_invite_code, hash_password
from app.models.auth import InviteCode, User
from app.models.story import Chapter, StoryBible, StoryProject

DATABASE_URL = os.environ.get("VSL_DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("VSL_DATABASE_URL must be set before seeding UAT data")

DEMO_INVITE_CODE = "DEMO2026"
TEST_ADMIN_ACCOUNT = os.environ.get("VSL_UAT_ADMIN_ACCOUNT") or f"uat-admin-{secrets.token_hex(4)}@wordflow.test"
TEST_ADMIN_PASSWORD = os.environ.get("VSL_UAT_ADMIN_PASSWORD") or secrets.token_urlsafe(18)
DEMO_STORY_TITLE = "Demo Adventure Story"


def ensure_invite_code(session: Session) -> None:
    code_hash = hash_invite_code(DEMO_INVITE_CODE)
    invite = session.scalar(select(InviteCode).where(InviteCode.code_hash == code_hash))
    if invite is None:
        session.add(InviteCode(code_hash=code_hash, max_uses=1000, used_count=0))
        return

    invite.max_uses = max(invite.max_uses, 1000)
    invite.expires_at = None
    session.add(invite)


def ensure_test_admin(session: Session) -> User:
    user = session.scalar(select(User).where(User.email == TEST_ADMIN_ACCOUNT))
    password_hash = hash_password(TEST_ADMIN_PASSWORD)
    if user is None:
        user = User(email=TEST_ADMIN_ACCOUNT, password_hash=password_hash, is_active=True)
    else:
        user.password_hash = password_hash
        user.is_active = True
    session.add(user)
    session.flush()
    return user


def ensure_demo_story(session: Session, user: User) -> None:
    project = session.scalar(
        select(StoryProject).where(
            StoryProject.user_id == user.id,
            StoryProject.title == DEMO_STORY_TITLE,
        )
    )
    if project is None:
        project = StoryProject(
            user_id=user.id,
            title=DEMO_STORY_TITLE,
            style="web_novel",
            target_chapter_count=5,
            current_chapter_number=1,
        )
        session.add(project)
        session.flush()

    story_bible = session.scalar(select(StoryBible).where(StoryBible.story_project_id == project.id))
    if story_bible is None:
        session.add(
            StoryBible(
                story_project_id=project.id,
                characters={
                    "Lily": "protagonist - curious student",
                    "Tom": "Lily's best friend",
                },
                worldview="A quiet village with hidden secrets",
                main_plot="Lily discovers an ancient book",
                tone="adventurous",
                immutable_facts={},
            )
        )

    existing_chapters = {
        chapter.chapter_number
        for chapter in session.scalars(select(Chapter).where(Chapter.story_project_id == project.id))
    }
    for chapter_number in range(1, 6):
        if chapter_number not in existing_chapters:
            session.add(Chapter(story_project_id=project.id, chapter_number=chapter_number, status="draft"))


def seed(engine: Engine) -> None:
    with Session(engine) as session:
        ensure_invite_code(session)
        user = ensure_test_admin(session)
        ensure_demo_story(session, user)
        session.commit()
        print(f"Demo data seeded. Invite code: {DEMO_INVITE_CODE}")
        print(f"Test admin account: {TEST_ADMIN_ACCOUNT}")


def main() -> None:
    engine = create_engine(DATABASE_URL)
    seed(engine)
    engine.dispose()


if __name__ == "__main__":
    main()
