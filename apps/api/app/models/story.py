import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class StoryProject(Base):
    __tablename__ = "story_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    style = Column(String(32), nullable=False)
    target_chapter_count = Column(Integer, nullable=False)
    current_chapter_number = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="story_projects")
    chapters = relationship("Chapter", back_populates="story_project", cascade="all, delete-orphan")
    story_bible = relationship("StoryBible", back_populates="story_project", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("story_project_id", "chapter_number"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_project_id = Column(ForeignKey("story_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_number = Column(Integer, nullable=False)
    status = Column(String(32), default="draft", nullable=False)
    english_content = Column(Text, nullable=True)
    chinese_translation = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    story_project = relationship("StoryProject", back_populates="chapters")
    chapter_state = relationship("ChapterState", back_populates="chapter", cascade="all, delete-orphan")
    target_words = relationship("ChapterTargetWord", back_populates="chapter", cascade="all, delete-orphan")


class StoryBible(Base):
    __tablename__ = "story_bibles"
    __table_args__ = (UniqueConstraint("story_project_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_project_id = Column(ForeignKey("story_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    characters = Column(JSON, default=dict, nullable=False)
    worldview = Column(Text, nullable=True)
    main_plot = Column(Text, nullable=True)
    tone = Column(Text, nullable=True)
    immutable_facts = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    story_project = relationship("StoryProject", back_populates="story_bible")


class ChapterState(Base):
    __tablename__ = "chapter_states"
    __table_args__ = (UniqueConstraint("chapter_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    unresolved_hooks = Column(JSON, default=list, nullable=False)
    character_states = Column(JSON, default=dict, nullable=False)
    continuity_constraints = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    chapter = relationship("Chapter", back_populates="chapter_state")
