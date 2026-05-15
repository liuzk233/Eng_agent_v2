import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class GenerationTask(Base):
    __tablename__ = "generation_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), default="queued", nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    fallback_reason = Column(Text, nullable=True)
    provider_name = Column(String(80), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    chapter = relationship("Chapter")
    quality_reports = relationship("QualityReport", back_populates="generation_task", cascade="all, delete-orphan")


class QualityReport(Base):
    __tablename__ = "quality_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_task_id = Column(ForeignKey("generation_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    out_of_syllabus_rate = Column(Float, default=0.0, nullable=False)
    out_of_syllabus_words = Column(JSON, default=list, nullable=False)
    target_word_hits = Column(JSON, default=dict, nullable=False)
    review_notes = Column(Text, nullable=True)
    passed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    generation_task = relationship("GenerationTask", back_populates="quality_reports")
    chapter = relationship("Chapter")
