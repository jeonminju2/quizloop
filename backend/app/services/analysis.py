"""오답분석/재출제 화면이 그대로 그릴 수 있는 형태로 채점 결과를 집계.

QuizSet(+가장 최근 Submission) 하나를 받아서:
  - 전체 정답률
  - 개념별 정답률 (concept_accuracy) - 재출제 화면의 before/after 비교에 그대로 재사용됨
  - 오답 유형 분포 (type_breakdown)
  - 틀린 문제 상세 (details, 근거 출처 포함)
을 계산한다.
"""

import uuid
from collections import defaultdict

from sqlalchemy.orm import Session

from app import models, schemas


def _latest_submission(db: Session, quiz_set_id: uuid.UUID, user_id: uuid.UUID) -> models.Submission | None:
    return (
        db.query(models.Submission)
        .filter(
            models.Submission.quiz_set_id == quiz_set_id,
            models.Submission.user_id == user_id,
        )
        .order_by(models.Submission.submitted_at.desc())
        .first()
    )


def _source_label(db: Session, question: models.Question) -> str | None:
    if not question.source_chunk_id:
        return None
    chunk = db.query(models.MaterialChunk).get(question.source_chunk_id)
    if not chunk:
        return None
    material = db.query(models.Material).get(chunk.material_id)
    title = material.title if material else "자료"
    page = f"p.{chunk.page_or_slide_no}" if chunk.page_or_slide_no else ""
    return f"{title} {page}".strip()


def get_quiz_analysis(db: Session, quiz_set_id: uuid.UUID, user_id: uuid.UUID) -> schemas.QuizAnalysisOut:
    submission = _latest_submission(db, quiz_set_id, user_id)
    if submission is None:
        raise ValueError("이 문제 세트에 대한 제출 기록이 없음")

    answers = (
        db.query(models.SubmissionAnswer)
        .filter(models.SubmissionAnswer.submission_id == submission.id)
        .all()
    )

    total = len(answers)
    correct = sum(1 for a in answers if a.is_correct)
    accuracy = correct / total if total else 0.0

    # 개념별 정답률 집계
    concept_stats: dict[uuid.UUID, dict] = defaultdict(lambda: {"correct": 0, "total": 0, "name": ""})
    type_counts: dict[str, int] = defaultdict(int)
    details: list[schemas.AnalysisDetail] = []

    for ans in answers:
        question = db.query(models.Question).get(ans.question_id)
        concept = db.query(models.Concept).get(question.concept_id)

        stat = concept_stats[question.concept_id]
        stat["name"] = concept.name if concept else "(개념 미지정)"
        stat["total"] += 1
        if ans.is_correct:
            stat["correct"] += 1

        if not ans.is_correct:
            tag = (
                db.query(models.WrongAnswerTag)
                .filter(models.WrongAnswerTag.submission_answer_id == ans.id)
                .first()
            )
            tag_type = tag.tag_type if tag else None
            if tag_type:
                type_counts[tag_type] += 1

            details.append(
                schemas.AnalysisDetail(
                    question_id=question.id,
                    question_text=question.question_text,
                    user_answer=ans.user_answer or "",
                    correct_answer=question.correct_answer,
                    tag_type=tag_type,
                    source_label=_source_label(db, question),
                )
            )

    concept_accuracy = [
        schemas.ConceptAccuracy(
            concept_id=cid,
            concept_name=s["name"],
            correct=s["correct"],
            total=s["total"],
            accuracy=(s["correct"] / s["total"]) if s["total"] else 0.0,
        )
        for cid, s in concept_stats.items()
    ]
    concept_accuracy.sort(key=lambda c: c.accuracy)  # 취약한(정답률 낮은) 순

    wrong_total = sum(type_counts.values())
    type_breakdown = [
        schemas.TypeBreakdownItem(
            tag_type=t,
            count=c,
            pct=(c / wrong_total) if wrong_total else 0.0,
        )
        for t, c in type_counts.items()
    ]

    return schemas.QuizAnalysisOut(
        quiz_set_id=quiz_set_id,
        submission_id=submission.id,
        total=total,
        correct=correct,
        accuracy=accuracy,
        concept_accuracy=concept_accuracy,
        type_breakdown=type_breakdown,
        details=details,
    )
