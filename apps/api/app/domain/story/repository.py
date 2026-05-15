from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.story import Chapter, StoryBible, StoryProject


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
                immutable_facts={},
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
