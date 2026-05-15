from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.story import Chapter, ChapterState, StoryBible, StoryProject


class ContinuityRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_story_bible(self, story_project_id: UUID) -> StoryBible | None:
        return self.session.scalar(
            select(StoryBible).where(StoryBible.story_project_id == story_project_id)
        )

    def get_chapter_state(self, chapter_id: UUID) -> ChapterState | None:
        return self.session.scalar(
            select(ChapterState).where(ChapterState.chapter_id == chapter_id)
        )

    def get_previous_chapter_state(
        self, story_project_id: UUID, current_chapter_number: int
    ) -> ChapterState | None:
        if current_chapter_number <= 1:
            return None
        prev_chapter = self.session.scalar(
            select(Chapter).where(
                Chapter.story_project_id == story_project_id,
                Chapter.chapter_number == current_chapter_number - 1,
            )
        )
        if prev_chapter is None:
            return None
        return self.session.scalar(
            select(ChapterState).where(ChapterState.chapter_id == prev_chapter.id)
        )

    def update_story_bible(
        self,
        story_project_id: UUID,
        *,
        characters: dict | None = None,
        worldview: str | None = None,
        main_plot: str | None = None,
        tone: str | None = None,
        immutable_facts: dict | None = None,
    ) -> StoryBible:
        bible = self.get_story_bible(story_project_id)
        if bible is None:
            raise ValueError(f"StoryBible not found for project {story_project_id}")
        if characters is not None:
            bible.characters = characters
        if worldview is not None:
            bible.worldview = worldview
        if main_plot is not None:
            bible.main_plot = main_plot
        if tone is not None:
            bible.tone = tone
        if immutable_facts is not None:
            bible.immutable_facts = immutable_facts
        self.session.flush()
        return bible

    def update_chapter_state(
        self,
        chapter_id: UUID,
        *,
        summary: str | None = None,
        unresolved_hooks: list | None = None,
        character_states: dict | None = None,
        continuity_constraints: dict | None = None,
    ) -> ChapterState:
        state = self.get_chapter_state(chapter_id)
        if state is None:
            state = ChapterState(chapter_id=chapter_id)
            self.session.add(state)
            self.session.flush()
        if summary is not None:
            state.summary = summary
        if unresolved_hooks is not None:
            state.unresolved_hooks = unresolved_hooks
        if character_states is not None:
            state.character_states = character_states
        if continuity_constraints is not None:
            state.continuity_constraints = continuity_constraints
        self.session.flush()
        return state


class ContinuityService:
    def __init__(self, repository: ContinuityRepository):
        self.repository = repository

    def get_continuity_context(
        self, story_project_id: UUID, chapter_number: int
    ) -> dict:
        bible = self.repository.get_story_bible(story_project_id)
        prev_state = self.repository.get_previous_chapter_state(
            story_project_id, chapter_number
        )
        return {
            "story_bible": {
                "characters": bible.characters if bible else {},
                "worldview": bible.worldview if bible else None,
                "main_plot": bible.main_plot if bible else None,
                "tone": bible.tone if bible else None,
                "immutable_facts": bible.immutable_facts if bible else {},
            },
            "previous_chapter": {
                "summary": prev_state.summary if prev_state else None,
                "unresolved_hooks": prev_state.unresolved_hooks if prev_state else [],
                "character_states": prev_state.character_states if prev_state else {},
                "continuity_constraints": prev_state.continuity_constraints if prev_state else {},
            },
        }

    def update_story_bible(
        self, story_project_id: UUID, **kwargs: object
    ) -> StoryBible:
        return self.repository.update_story_bible(story_project_id, **kwargs)

    def update_chapter_state(
        self, chapter_id: UUID, **kwargs: object
    ) -> ChapterState:
        return self.repository.update_chapter_state(chapter_id, **kwargs)
