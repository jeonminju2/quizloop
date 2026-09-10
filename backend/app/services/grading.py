"""채점 로직. 객관식은 정답 비교, 단답형은 우선 키워드/정확매치로 시작하고
추후 LLM 기반 유사도 채점으로 교체 (TODO)."""

import uuid

from sqlalchemy.orm import Session

from app import models


def grade_answer(question: models.Question, user_answer: str) -> bool:
    if question.type == "multiple_choice":
        return user_answer.strip() == question.correct_answer.strip()

    # short_answer: MVP는 정확 매치(공백/대소문자 무시). TODO: LLM 채점으로 교체.
    return user_answer.strip().lower() == question.correct_answer.strip().lower()


def grade_submission(db: Session, quiz_set_id: uuid.UUID, user_id: uuid.UUID, answers: list[dict]) -> models.Submission:
    submission = models.Submission(user_id=user_id, quiz_set_id=quiz_set_id)
    db.add(submission)
    db.flush()

    correct_count = 0
    for ans in answers:
        question = db.query(models.Question).get(ans["question_id"])
        is_correct = grade_answer(question, ans["user_answer"])
        correct_count += int(is_correct)

        db.add(
            models.SubmissionAnswer(
                submission_id=submission.id,
                question_id=question.id,
                user_answer=ans["user_answer"],
                is_correct=is_correct,
            )
        )

    submission.score = correct_count / len(answers) if answers else 0.0
    db.commit()
    return submission
