from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.auth import router as auth_router
from app.api.routes.chapter_words import router as chapter_words_router
from app.api.routes.generation import router as generation_router
from app.api.routes.story_projects import router as story_projects_router
from app.api.routes.vocabularies import router as vocabularies_router
from app.core.config import settings
from app.db.session import get_db

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(story_projects_router)
api_router.include_router(vocabularies_router)
api_router.include_router(chapter_words_router)
api_router.include_router(generation_router)


@api_router.get("/health/live", tags=["health"])
def live() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
    }


@api_router.get("/health", tags=["health"])
@api_router.get("/health/ready", tags=["health"])
def ready(session: Session = Depends(get_db)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "service": settings.app_name,
        "database": "ok",
    }
