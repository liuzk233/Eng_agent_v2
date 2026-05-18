from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.story import Chapter, StoryBible, StoryProject


STYLE_TONES = {
    "web_novel": "Fast progression, visible power shifts, and a hook at each chapter ending.",
    "science_fiction": "Speculative discovery, concrete stakes, and continuity across each chapter.",
    "exam_reading": "Clear informational structure for focused reading practice.",
}


class StoryProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_story_project(
        self,
        user: User,
        title: str,
        style: str,
        target_chapter_count: int,
    ) -> StoryProject:
        chapter_outline = _build_initial_chapter_outline(target_chapter_count)
        project = StoryProject(
            user_id=user.id,
            title=title,
            style=style,
            target_chapter_count=target_chapter_count,
            current_chapter_number=1,
        )
        self.session.add(project)
        self.session.flush()

        self.session.add(
            StoryBible(
                story_project_id=project.id,
                characters={},
                main_plot=_build_initial_main_plot(title, style, target_chapter_count, chapter_outline),
                tone=STYLE_TONES.get(style),
                immutable_facts={"chapter_outline": chapter_outline},
            )
        )
        for chapter_number in range(1, target_chapter_count + 1):
            self.session.add(
                Chapter(
                    story_project_id=project.id,
                    chapter_number=chapter_number,
                    status="draft",
                )
            )
        self.session.flush()
        return project

    def list_story_projects(self, user: User, *, limit: int = 50, offset: int = 0) -> list[StoryProject]:
        return list(
            self.session.scalars(
                select(StoryProject)
                .where(StoryProject.user_id == user.id)
                .order_by(StoryProject.created_at, StoryProject.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def get_story_project_for_user(self, user: User, story_project_id: UUID) -> StoryProject | None:
        return self.session.scalar(
            select(StoryProject).where(
                StoryProject.id == story_project_id,
                StoryProject.user_id == user.id,
            )
        )


def _build_initial_main_plot(
    title: str,
    style: str,
    target_chapter_count: int,
    outline: list[str],
) -> str:
    return (
        f"Initial outline for '{title}' ({style}, {target_chapter_count} chapter(s)): "
        + " ".join(outline)
    )


def _build_initial_chapter_outline(target_chapter_count: int) -> list[str]:
    if target_chapter_count <= 1:
        return ["Chapter 1 establishes the premise, develops the target words, and closes the short arc."]

    outline: list[str] = []
    for chapter_number in range(1, target_chapter_count + 1):
        if chapter_number == 1:
            purpose = "opens the premise, introduces the pressure, and ends with a forward hook"
        elif chapter_number == target_chapter_count:
            purpose = "resolves the central tension while preserving vocabulary clarity"
        else:
            purpose = "escalates the conflict and carries unresolved details into the next chapter"
        outline.append(f"Chapter {chapter_number} {purpose}.")
    return outline
