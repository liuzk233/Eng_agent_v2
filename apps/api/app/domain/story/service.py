from uuid import UUID

from app.domain.story.repository import StoryProjectRepository
from app.models.auth import User
from app.models.story import StoryProject
from app.schemas.story import CreateStoryProjectRequest, RenameStoryProjectRequest


class StoryProjectError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


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

    def rename_story_project(
        self,
        user: User,
        story_project_id: UUID,
        payload: RenameStoryProjectRequest,
    ) -> StoryProject:
        project = self.repository.update_story_project_title_for_user(user, story_project_id, payload.title)
        if project is None:
            raise StoryProjectError("Story project not found", 404)

        self.repository.session.commit()
        self.repository.session.refresh(project)
        return project

    def delete_story_project(self, user: User, story_project_id: UUID) -> None:
        deleted = self.repository.delete_story_project_for_user(user, story_project_id)
        if not deleted:
            raise StoryProjectError("Story project not found", 404)

        self.repository.session.commit()
