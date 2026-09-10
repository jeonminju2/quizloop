import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.question_generation import (
    generate_initial_questions,
    regenerate_from_weak_concepts,
)
from app.services.grading import grade_submission
from app.services.wrong_answer_analysis import classify_wrong_answer, update_weak_concept_stats
from app.services.analysis import get_quiz_analysis

router = APIRouter(prefix="/quiz-sets", tags=["quiz"])


@router.post("/generate", response_model=schemas.QuizSetOut)
def generate(
    req: schemas.QuizGenerateRequest,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return generate_initial_questions(
        db,
        user_id=user_id,
        material_id=req.material_id,
        num_questions=req.num_questions,
        difficulty=req.difficulty,
        question_types=req.question_types,
    )


@router.get("/{quiz_set_id}", response_model=schemas.QuizSetOut)
def get_quiz_set(quiz_set_id: uuid.UUID, db: Session = Depends(get_db)):
    """새로고침·직접 URL 진입 시 문제 세트를 다시 불러오기 위한 엔드포인트."""
    quiz_set = db.query(models.QuizSet).get(quiz_set_id)
    if quiz_set is None:
        raise HTTPException(status_code=404, detail="문제 세트를 찾을 수 없음")
    return quiz_set


@router.post("/{quiz_set_id}/submit", response_model=schemas.SubmissionOut)
def submit(
    quiz_set_id: uuid.UUID,
    req: schemas.SubmissionCreate,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    submission = grade_submission(
        db,
        quiz_set_id=quiz_set_id,
        user_id=user_id,
        answers=[a.model_dump() for a in req.answers],
    )

    # 오답만 분류 + 취약개념 집계 업데이트
    for answer in submission.answers:
        question = db.query(models.Question).get(answer.question_id)
        if not answer.is_correct:
            classify_wrong_answer(db, answer)
        update_weak_concept_stats(
            db, user_id=user_id, concept_id=question.concept_id, was_wrong=not answer.is_correct
        )

    return submission


@router.post("/regenerate", response_model=schemas.QuizSetOut)
def regenerate(
    req: schemas.RegenerateRequest,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    source = db.query(models.QuizSet).get(req.source_quiz_set_id)

    # 취약도(weak_score) 상위 개념들만 골라서 재출제
    weak_stats = (
        db.query(models.WeakConceptStat)
        .filter(models.WeakConceptStat.user_id == user_id)
        .order_by(models.WeakConceptStat.weak_score.desc())
        .limit(5)
        .all()
    )

    return regenerate_from_weak_concepts(
        db,
        user_id=user_id,
        source_quiz_set=source,
        weak_concept_stats=weak_stats,
        num_questions=req.num_questions,
    )


@router.get("/{quiz_set_id}/analysis", response_model=schemas.QuizAnalysisOut)
def analysis(
    quiz_set_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """오답분석/재출제 화면이 바로 그릴 수 있는 형태로 채점 결과를 집계해서 반환.
    재출제 화면의 before/after 비교는 이 엔드포인트를 (원본 quiz_set_id, 재출제 quiz_set_id)
    두 번 호출해서 concept_accuracy를 개념별로 매칭하면 된다.
    """
    try:
        return get_quiz_analysis(db, quiz_set_id=quiz_set_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
