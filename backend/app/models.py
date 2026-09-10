"""SQLAlchemy 모델. docs/DB스키마.md 의 테이블 정의를 그대로 코드로 옮긴 것.
스키마를 고치면 이 파일도 같이 고칠 것.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    materials: Mapped[list["Material"]] = relationship(back_populates="user")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)  # pdf / ppt / txt
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="materials")
    chunks: Mapped[list["MaterialChunk"]] = relationship(back_populates="material")
    concepts: Mapped[list["Concept"]] = relationship(back_populates="material")


class MaterialChunk(Base):
    __tablename__ = "material_chunks"

    id: Mapped[uuid.UUID] = uuid_pk()
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("materials.id"), nullable=False)
    page_or_slide_no: Mapped[int] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(settings.embedding_dim), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    material: Mapped["Material"] = relationship(back_populates="chunks")


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[uuid.UUID] = uuid_pk()
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("materials.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    parent_concept_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("concepts.id"), nullable=True
    )

    material: Mapped["Material"] = relationship(back_populates="concepts")


class QuizSet(Base):
    __tablename__ = "quiz_sets"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("materials.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, default="initial")  # initial / regenerated
    source_quiz_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quiz_sets.id"), nullable=True
    )
    target_concept_ids: Mapped[list] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    difficulty: Mapped[str] = mapped_column(String, default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    questions: Mapped[list["Question"]] = relationship(back_populates="quiz_set")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = uuid_pk()
    quiz_set_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quiz_sets.id"), nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("concepts.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # multiple_choice / short_answer
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    source_chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("material_chunks.id"), nullable=True
    )

    quiz_set: Mapped["QuizSet"] = relationship(back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(back_populates="question")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[uuid.UUID] = uuid_pk()
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id"), nullable=False)
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    option_order: Mapped[int] = mapped_column(Integer, default=0)

    question: Mapped["Question"] = relationship(back_populates="options")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    quiz_set_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quiz_sets.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    answers: Mapped[list["SubmissionAnswer"]] = relationship(back_populates="submission")


class SubmissionAnswer(Base):
    __tablename__ = "submission_answers"

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submissions.id"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id"), nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="answers")
    wrong_tag: Mapped["WrongAnswerTag"] = relationship(
        back_populates="submission_answer", uselist=False
    )


class WrongAnswerTag(Base):
    __tablename__ = "wrong_answer_tags"

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_answer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submission_answers.id"), nullable=False
    )
    tag_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # careless_mistake / concept_confusion / not_learned
    confused_with_concept_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("concepts.id"), nullable=True
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)

    submission_answer: Mapped["SubmissionAnswer"] = relationship(back_populates="wrong_tag")


class WeakConceptStat(Base):
    __tablename__ = "weak_concept_stats"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("concepts.id"), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    weak_score: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
