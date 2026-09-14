"""문제 생성 오케스트레이션: DB에서 개념/청크 조회 -> 프롬프트 조립 -> LLM 호출 -> 검증 -> 저장."""

import uuid

from sqlalchemy.orm import Session

from app import models
from app.prompts.question_generation_v1 import (
    QUESTION_GENERATION_TOOL_SCHEMA,
    SYSTEM_PROMPT,
    build_regeneration_user_prompt,
    build_user_prompt,
)
from app.services.ingestion import embed_query
from app.services.llm_client import call_with_tool_schema


def _select_chunks_for_material(
    db: Session, material_id: uuid.UUID, query_text: str | None = None, limit: int = 20
):
    """query_text가 주어지면 그걸 임베딩해서 pgvector 코사인 유사도 순으로 관련 청크만 추린다
    (RAG 검색 단계). query_text가 없거나, VOYAGE_API_KEY가 없어서 임베딩을 못 만들거나,
    이 자료의 청크에 임베딩이 없으면(임베딩 켜기 전에 업로드된 자료) 기존처럼
    "자료의 청크를 그대로 상위 limit개" 가져오는 걸로 폴백한다.
    """
    base_query = db.query(models.MaterialChunk).filter(models.MaterialChunk.material_id == material_id)

    if query_text:
        query_embedding = embed_query(query_text)
        if query_embedding is not None:
            return (
                base_query.filter(models.MaterialChunk.embedding.isnot(None))
                .order_by(models.MaterialChunk.embedding.cosine_distance(query_embedding))
                .limit(limit)
                .all()
            )

    return base_query.limit(limit).all()


def _persist_questions(
    db: Session, quiz_set: models.QuizSet, raw_questions: list[dict], concept_name_to_id: dict
) -> list[models.Question]:
    saved: list[models.Question] = []
    for q in raw_questions:
        concept_id = concept_name_to_id.get(q["concept"])
        if concept_id is None:
            # LLM이 목록에 없는 개념명을 만들어낸 경우 - 스킵하고 로그만 남김 (운영 시엔 재시도 로직으로 교체)
            continue

        question = models.Question(
            quiz_set_id=quiz_set.id,
            concept_id=concept_id,
            type=q["type"],
            question_text=q["question_text"],
            correct_answer=q["correct_answer"],
            explanation=q.get("explanation"),
            source_chunk_id=q.get("source_chunk_id") or None,
        )
        db.add(question)
        db.flush()  # question.id 확보

        if q["type"] == "multiple_choice":
            for idx, opt in enumerate(q.get("options", [])):
                # v2: LLM이 표시한 related_concept(개념명)을 concept_id로 변환해서 저장 —
                # 오답분석(wrong_answer_analysis.py)이 매번 LLM 추론 없이 바로 조회할 수 있게.
                # 목록에 없는 이름이거나 빈 문자열이면 None (LLM 추론 폴백 경로를 타게 됨).
                related_concept_id = concept_name_to_id.get(opt.get("related_concept") or "")
                db.add(
                    models.QuestionOption(
                        question_id=question.id,
                        option_text=opt["text"],
                        is_correct=opt["is_correct"],
                        option_order=idx,
                        related_concept_id=related_concept_id,
                    )
                )
        saved.append(question)

    db.commit()
    return saved


def generate_initial_questions(
    db: Session,
    user_id: uuid.UUID,
    material_id: uuid.UUID,
    num_questions: int,
    difficulty: str,
    question_types: list[str],
) -> models.QuizSet:
    material = db.query(models.Material).get(material_id)
    concepts = db.query(models.Concept).filter(models.Concept.material_id == material_id).all()
    # 대상 개념명을 질의로 삼아 벡터 유사도 검색 — 개념과 무관한 청크를 걸러내기 위함
    # (임베딩이 없는 자료면 _select_chunks_for_material이 자동으로 "청크 전부"로 폴백).
    query_text = " ".join(c.name for c in concepts)
    chunks = _select_chunks_for_material(db, material_id, query_text=query_text)

    concept_dicts = [{"id": str(c.id), "name": c.name, "description": c.description or ""} for c in concepts]
    chunk_dicts = [
        {"id": str(c.id), "content": c.content, "page_or_slide_no": c.page_or_slide_no}
        for c in chunks
    ]
    concept_name_to_id = {c.name: c.id for c in concepts}

    user_prompt = build_user_prompt(
        material_title=material.title,
        concepts=concept_dicts,
        chunks=chunk_dicts,
        num_questions=num_questions,
        difficulty=difficulty,
        question_types=question_types,
        exam_style_note=material.exam_style_note,
    )

    result = call_with_tool_schema(SYSTEM_PROMPT, user_prompt, QUESTION_GENERATION_TOOL_SCHEMA)

    quiz_set = models.QuizSet(
        user_id=user_id,
        material_id=material_id,
        type="initial",
        difficulty=difficulty,
    )
    db.add(quiz_set)
    db.flush()

    _persist_questions(db, quiz_set, result["questions"], concept_name_to_id)
    return quiz_set


def regenerate_from_weak_concepts(
    db: Session,
    user_id: uuid.UUID,
    source_quiz_set: models.QuizSet,
    weak_concept_stats: list[models.WeakConceptStat],
    num_questions: int,
) -> models.QuizSet:
    material_id = source_quiz_set.material_id
    material = db.query(models.Material).get(material_id)

    weak_concepts = []
    concept_name_to_id = {}
    for stat in weak_concept_stats:
        concept = db.query(models.Concept).get(stat.concept_id)
        weak_concepts.append(
            {
                "id": str(concept.id),
                "name": concept.name,
                "description": concept.description or "",
                "wrong_count": stat.wrong_count,
            }
        )
        concept_name_to_id[concept.name] = concept.id

    # 취약 개념명을 질의로 삼아 벡터 유사도 검색 — 재출제는 특히 그 개념들과 관련된
    # 청크가 우선 뽑혀야 하므로 초기 생성보다 더 중요한 지점.
    query_text = " ".join(c["name"] for c in weak_concepts)
    chunks = _select_chunks_for_material(db, material_id, query_text=query_text)

    previous_questions = [q.question_text for q in source_quiz_set.questions]
    chunk_dicts = [
        {"id": str(c.id), "content": c.content, "page_or_slide_no": c.page_or_slide_no}
        for c in chunks
    ]

    user_prompt = build_regeneration_user_prompt(
        material_title=material.title,
        weak_concepts=weak_concepts,
        chunks=chunk_dicts,
        num_questions=num_questions,
        previous_questions=previous_questions,
        exam_style_note=material.exam_style_note,
    )

    result = call_with_tool_schema(SYSTEM_PROMPT, user_prompt, QUESTION_GENERATION_TOOL_SCHEMA)

    new_quiz_set = models.QuizSet(
        user_id=user_id,
        material_id=material_id,
        type="regenerated",
        source_quiz_set_id=source_quiz_set.id,
        target_concept_ids=[c.concept_id for c in weak_concept_stats],
        difficulty=source_quiz_set.difficulty,
    )
    db.add(new_quiz_set)
    db.flush()

    _persist_questions(db, new_quiz_set, result["questions"], concept_name_to_id)
    return new_quiz_set
