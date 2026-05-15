import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ExamSyllabus(Base):
    __tablename__ = "exam_syllabi"
    __table_args__ = (UniqueConstraint("code", "version"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(64), nullable=False)
    name = Column(String(160), nullable=False)
    version = Column(String(64), nullable=False)
    source_description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    words = relationship("SyllabusWord", back_populates="syllabus", cascade="all, delete-orphan")


class SyllabusWord(Base):
    __tablename__ = "syllabus_words"
    __table_args__ = (UniqueConstraint("syllabus_id", "lemma"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    syllabus_id = Column(ForeignKey("exam_syllabi.id", ondelete="CASCADE"), nullable=False, index=True)
    lemma = Column(String(120), nullable=False, index=True)
    allowed_forms = Column(JSON, default=list, nullable=False)
    part_of_speech = Column(String(64), nullable=True)
    definition_cn = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    syllabus = relationship("ExamSyllabus", back_populates="words")


class ChapterTargetWord(Base):
    __tablename__ = "chapter_target_words"
    __table_args__ = (UniqueConstraint("chapter_id", "lemma"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    word = Column(String(120), nullable=False)
    lemma = Column(String(120), nullable=False, index=True)
    source = Column(String(32), nullable=False)
    position = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chapter = relationship("Chapter", back_populates="target_words")
