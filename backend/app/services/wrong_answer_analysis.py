"""오답 유형 분류 + 취약개념 집계.

문제 생성 프롬프트(v1)와 별개로, 오답 분석용 프롬프트는 아직 v1 설계 전 — 여기는 뼈대만 잡아둠.
TODO: docs/오답분석-프롬프트-v1.md 로 별도 설계 예정 (요청 시 진행).
"""

import uuid

from sqlalchemy.orm import Session

from app import models
from app.services.llm_client import get_client
from app.config import settings

# 최소 버전 스키마 — 추후 concept_generation_v1과 동일한 방식(tool_choice 강제)으로 확장 예정
WRONG_ANSWER_TAG_TOOL_SCHEMA = {
    "name": "submit_wrong_answer_tag",
    "description": "오답 하나를 분류한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tag_type": {
                "type": "string",
                "enum": ["careless_mistake", "concept_confusion", "not_learned"],
            },
            "confused_with_concept": {
                "type": "string",
                "description": "concept_confusion일 때, 헷갈렸다고 판단되는 다른 개념명. 아니면 빈 문자열.",
            },
            "reasoning": {"type": "string"},
        },
        "required": ["tag_type", "reasoning"],
    },
}


def classify_wrong_answer(
    db: Session, submission_answer: models.SubmissionAnswer
) -> models.WrongAnswerTag:
    question = db.query(models.Question).get(submission_answer.question_id)

    system_prompt = (
        "당신은 학생의 오답을 분석하는 채점 보조 AI입니다. "
        "문제, 정답, 학생 답안을 보고 오답 유형을 careless_mistake(단순 실수) / "
        "concept_confusion(다른 개념과 혼동) / not_learned(개념을 아예 모름) 중 하나로 분류하세요."
    )
    user_prompt = (
        f"[문제] {question.question_text}\n"
        f"[정답] {question.correct_answer}\n"
        f"[학생 답안] {submission_answer.user_answer}\n"
        f"[해설] {question.explanation}\n\n"
        "submit_wrong_answer_tag 도구로 분류 결과를 제출하세요."
    )

    client = get_client()
    response = client.messages.create(
        model=settings.llm_model,
        max_tokens=512,
        system=system_prompt,
        tools=[WRONG_ANSWER_TAG_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_wrong_answer_tag"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    result = next(b.input for b in response.content if b.type == "tool_use")

    confused_concept_id = None
    if result.get("confused_with_concept"):
        confused = (
            db.query(models.Concept)
            .filter(models.Concept.name == result["confused_with_concept"])
            .first()
        )
        confused_concept_id = confused.id if confused else None

    tag = models.WrongAnswerTag(
        submission_answer_id=submission_answer.id,
        tag_type=result["tag_type"],
        confused_with_concept_id=confused_concept_id,
        reasoning=result.get("reasoning"),
    )
    db.add(tag)
    db.commit()
    return tag


def update_weak_concept_stats(db: Session, user_id: uuid.UUID, concept_id: uuid.UUID, was_wrong: bool):
    stat = (
        db.query(models.WeakConceptStat)
        .filter(
            models.WeakConceptStat.user_id == user_id,
            models.WeakConceptStat.concept_id == concept_id,
        )
        .first()
    )
    if stat is None:
        stat = models.WeakConceptStat(user_id=user_id, concept_id=concept_id)
        db.add(stat)

    stat.attempt_count += 1
    if was_wrong:
        stat.wrong_count += 1
    stat.weak_score = stat.wrong_count / stat.attempt_count if stat.attempt_count else 0.0
    db.commit()
