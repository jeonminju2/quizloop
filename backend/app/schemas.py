"""API 요청/응답용 Pydantic 스키마."""

import uuid
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="최소 8자")
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Materials ----------

class MaterialOut(BaseModel):
    id: uuid.UUID
    title: str
    file_type: str
    status: str
    exam_style_note: Optional[str] = None

    class Config:
        from_attributes = True


class MaterialUpdate(BaseModel):
    """지금은 exam_style_note만 수정 가능 (업로드 이후에도 자유롭게 갱신할 수 있게)."""

    exam_style_note: Optional[str] = None


# ---------- Quiz generation ----------

class QuizGenerateRequest(BaseModel):
    material_id: uuid.UUID
    num_questions: int = 10
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    question_types: list[Literal["multiple_choice", "short_answer"]] = [
        "multiple_choice",
        "short_answer",
    ]
    concept_ids: Optional[list[uuid.UUID]] = None  # 특정 개념만 출제하고 싶을 때


class QuestionOptionOut(BaseModel):
    option_text: str
    option_order: int

    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    id: uuid.UUID
    type: str
    question_text: str
    options: list[QuestionOptionOut] = []

    class Config:
        from_attributes = True


class QuizSetOut(BaseModel):
    id: uuid.UUID
    type: str
    difficulty: str
    material_id: uuid.UUID
    source_quiz_set_id: Optional[uuid.UUID] = None
    questions: list[QuestionOut]

    class Config:
        from_attributes = True


# ---------- Submission ----------

class AnswerIn(BaseModel):
    question_id: uuid.UUID
    user_answer: str


class SubmissionCreate(BaseModel):
    quiz_set_id: uuid.UUID
    answers: list[AnswerIn]


class WrongAnswerTagOut(BaseModel):
    tag_type: str
    reasoning: Optional[str] = None

    class Config:
        from_attributes = True


class SubmissionAnswerOut(BaseModel):
    question_id: uuid.UUID
    user_answer: str
    is_correct: bool
    wrong_tag: Optional[WrongAnswerTagOut] = None

    class Config:
        from_attributes = True


class SubmissionOut(BaseModel):
    id: uuid.UUID
    score: float
    answers: list[SubmissionAnswerOut]

    class Config:
        from_attributes = True


# ---------- Regenerate ----------

class RegenerateRequest(BaseModel):
    source_quiz_set_id: uuid.UUID
    num_questions: int = 5


# ---------- Analysis ----------
# 프론트 오답분석/재출제 화면이 그대로 그릴 수 있는 형태로 집계해서 내려준다.
# (프론트에서 questions/submissions/concepts를 따로 join하지 않아도 되게)

class ConceptAccuracy(BaseModel):
    concept_id: uuid.UUID
    concept_name: str
    correct: int
    total: int
    accuracy: float  # 0.0 ~ 1.0


class TypeBreakdownItem(BaseModel):
    tag_type: str  # careless_mistake / concept_confusion / not_learned
    count: int
    pct: float  # 0.0 ~ 1.0


class AnalysisDetail(BaseModel):
    question_id: uuid.UUID
    question_text: str
    user_answer: str
    correct_answer: str
    tag_type: Optional[str] = None
    source_label: Optional[str] = None  # 예: "6장 p.12"


class QuizAnalysisOut(BaseModel):
    quiz_set_id: uuid.UUID
    submission_id: uuid.UUID
    total: int
    correct: int
    accuracy: float
    concept_accuracy: list[ConceptAccuracy]
    type_breakdown: list[TypeBreakdownItem]
    details: list[AnalysisDetail]  # 틀린 문제만
