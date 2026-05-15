from uuid import UUID

from app.domain.story.repository import StoryProjectRepository
from app.models.auth import User
from app.models.story import StoryProject
from app.schemas.story import CreateStoryProjectRequest


class StoryProjectService:
    def __init__(self, repository: StoryProjectRepository):
        self.repository = repository

    def create_story_project(self, user: User, payload: CreateStoryProjectRequest) -> StoryProject:
        project = self.repository.create_story_project(
            user=user,
            title=payload.title.strip(),
            style=payload.style.value,
            target_chapter_count=payload.target_chapter_count,
        )
        self.repository.session.commit()
        self.repository.session.refresh(project)
        return project

    def list_story_projects(self, user: User, *, limit: int = 50, offset: int = 0) -> list[StoryProject]:
        return self.repository.list_story_projects(user, limit=limit, offset=offset)

    def get_story_project(self, user: User, story_project_id: UUID) -> StoryProject | None:
        return self.repository.get_story_project_for_user(user, story_project_id)
