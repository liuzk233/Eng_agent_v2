from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.session import get_db
from app.domain.story.repository import StoryProjectRepository
from app.domain.story.service import StoryProjectError, StoryProjectService
from app.models.auth import User
from app.models.story import StoryProject
from app.schemas.story import CreateStoryProjectRequest, RenameStoryProjectRequest, StoryProjectResponse

router = APIRouter(prefix="/api/story-projects", tags=["story-projects"])


def get_story_project_service(session: Session = Depends(get_db)) -> StoryProjectService:
    return StoryProjectService(StoryProjectRepository(session))


@router.post("", response_model=StoryProjectResponse, status_code=status.HTTP_201_CREATED)
def create_story_project(
    payload: CreateStoryProjectRequest,
    current_user: User = Depends(get_current_user),
    story_service: StoryProjectService = Depends(get_story_project_service),
) -> StoryProject:
    return story_service.create_story_project(current_user, payload)


@router.get("", response_model=list[StoryProjectResponse])
def list_story_projects(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: User = Depends(get_current_user),
    story_service: StoryProjectService = Depends(get_story_project_service),
) -> list[StoryProject]:
    return story_service.list_story_projects(current_user, limit=limit, offset=offset)


@router.get("/{story_project_id}", response_model=StoryProjectResponse)
def get_story_project(
    story_project_id: UUID,
    current_user: User = Depends(get_current_user),
    story_service: StoryProjectService = Depends(get_story_project_service),
) -> StoryProject:
    project = story_service.get_story_project(current_user, story_project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story project not found")
    return project


@router.patch("/{story_project_id}", response_model=StoryProjectResponse)
def rename_story_project(
    story_project_id: UUID,
    payload: RenameStoryProjectRequest,
    current_user: User = Depends(get_current_user),
    story_service: StoryProjectService = Depends(get_story_project_service),
) -> StoryProject:
    try:
        return story_service.rename_story_project(current_user, story_project_id, payload)
    except StoryProjectError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error
