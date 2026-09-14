"""오답 유형 분류 + 취약개념 집계.

분류 자체는 app/prompts/wrong_answer_analysis_v1.py (설계 배경은 docs/오답분석-프롬프트-v1.md)를
tool_choice 강제 방식(call_with_tool_schema)으로 호출해서 수행한다.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app import models
from app.prompts.wrong_answer_analysis_v1 import (
    SYSTEM_PROMPT,
    WRONG_ANSWER_ANALYSIS_TOOL_SCHEMA,
    build_user_prompt,
)

logger = logging.getLogger(__name__)


def classify_wrong_answer(
    db: Session, submission_answer: models.SubmissionAnswer
) -> models.WrongAnswerTag:
    question = db.query(models.Question).get(submission_answer.question_id)
    user_answer = (submission_answer.user_answer or "").strip()

    # 규칙: 답안이 비어있으면 LLM 호출 없이 바로 not_learned로 처리 (비용 절감 + 자명한 케이스)
    if not user_answer:
        tag = models.WrongAnswerTag(
            submission_answer_id=submission_answer.id,
            tag_type="not_learned",
            reasoning="답안을 작성하지 않음",
        )
        db.add(tag)
        db.commit()
        return tag

    option_rows = []
    options = None
    if question.type == "multiple_choice":
        option_rows = (
            db.query(models.QuestionOption)
            .filter(models.QuestionOption.question_id == question.id)
            .order_by(models.QuestionOption.option_order)
            .all()
        )
        options = [{"text": o.option_text, "is_correct": o.is_correct} for o in option_rows]

        # v2: 학생이 고른 오답 보기에 related_concept_id가 문제 생성 시점에 이미 박혀있으면
        # (question_generation.py의 _persist_questions, prompts/question_generation_v1.py 참고)
        # 매번 LLM에게 "무슨 개념이랑 헷갈렸는지" 추론시키지 않고 바로 조회해서 판정한다
        # (docs/오답분석-프롬프트-v1.md의 "알려진 한계"에서 지적했던 부분의 개선).
        # related_concept_id가 없거나(LLM이 이번엔 특정 개념과 안 엮었거나, v2 이전에 생성된 문제)
        # 대상 개념과 같으면(=오답인데 정답 개념으로 표시됨, 비정상 케이스) 기존 LLM 경로로 폴백한다.
        selected_option = next((o for o in option_rows if o.option_text == user_answer), None)
        if (
            selected_option is not None
            and selected_option.related_concept_id is not None
            and selected_option.related_concept_id != question.concept_id
        ):
            tag = models.WrongAnswerTag(
                submission_answer_id=submission_answer.id,
                tag_type="concept_confusion",
                confused_with_concept_id=selected_option.related_concept_id,
                reasoning="문제 생성 시점에 이 오답 보기가 헷갈리도록 설계된 개념으로 미리 표시되어 있어 LLM 호출 없이 바로 판정함",
            )
            db.add(tag)
            db.commit()
            return tag

    quiz_set = db.query(models.QuizSet).get(question.quiz_set_id)
    target_concept = db.query(models.Concept).get(question.concept_id)

    other_concepts = (
        db.query(models.Concept)
        .filter(
            models.Concept.material_id == quiz_set.material_id,
            models.Concept.id != question.concept_id,
        )
        .all()
    )

    user_prompt = build_user_prompt(
        question_text=question.question_text,
        question_type=question.type,
        options=options,
        correct_answer=question.correct_answer,
        user_answer=submission_answer.user_answer or "",
        explanation=question.explanation,
        target_concept={"name": target_concept.name, "description": target_concept.description or ""},
        other_concepts=[
            {"name": c.name, "description": c.description or ""} for c in other_concepts
        ],
    )

    from app.services.llm_client import call_with_tool_schema  # 순환 import 방지용 지연 import

    try:
        result = call_with_tool_schema(
            SYSTEM_PROMPT, user_prompt, WRONG_ANSWER_ANALYSIS_TOOL_SCHEMA
        )
    except Exception:
        logger.exception("classify_wrong_answer: LLM 호출 실패 — not_learned로 폴백하지 않고 표시만 함")
        tag = models.WrongAnswerTag(
            submission_answer_id=submission_answer.id,
            tag_type="not_learned",
            reasoning="분류 실패 (LLM 호출 에러) — 기본값으로 표시됨",
        )
        db.add(tag)
        db.commit()
        return tag

    confused_concept_id = None
    if result.get("confused_with_concept"):
        confused = next(
            (c for c in other_concepts if c.name == result["confused_with_concept"]), None
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
        # 컬럼의 default=0은 INSERT 시점에 DB로 보내는 값이라 flush 전까지는
        # 파이썬 객체 속성에 반영되지 않는다 — 여기서 명시적으로 0을 채워야
        # 바로 아래 += 연산이 None + int로 죽지 않는다.
        stat = models.WeakConceptStat(
            user_id=user_id, concept_id=concept_id, attempt_count=0, wrong_count=0
        )
        db.add(stat)

    stat.attempt_count += 1
    if was_wrong:
        stat.wrong_count += 1
    stat.weak_score = stat.wrong_count / stat.attempt_count if stat.attempt_count else 0.0
    db.commit()
