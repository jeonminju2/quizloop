"""자료 업로드 파이프라인: 텍스트 추출 -> 청크 분할 -> (임베딩) -> 핵심 개념 추출.

MaterialsRouter.upload_material()에서 파일을 저장한 뒤 process_material()을 호출하면
이 파일에 있는 단계들이 순서대로 돈다. 현재 임베딩 단계는 스텁(TODO) — 벡터 검색 provider를
정하면(voyage/openai 등) embed_chunks()만 채우면 된다. 텍스트 추출/청크 분할은 외부 API 없이
동작하고, 개념 추출은 ANTHROPIC_API_KEY가 있어야 동작한다 (없으면 건너뛰고 경고 로그만 남김).
"""

import logging
import uuid

from pypdf import PdfReader
from pptx import Presentation
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.prompts.concept_extraction_v1 import (
    CONCEPT_EXTRACTION_TOOL_SCHEMA,
    SYSTEM_PROMPT,
    build_user_prompt,
)

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 1200


# ---------- 1) 텍스트 추출 ----------

def extract_pages(file_path: str, file_type: str) -> list[dict]:
    """반환: [{"page_or_slide_no": int, "text": str}, ...] (빈 페이지는 제외)"""
    ft = file_type.lower().lstrip(".")
    if ft == "pdf":
        return _extract_pdf(file_path)
    if ft in ("ppt", "pptx"):
        return _extract_pptx(file_path)
    raise ValueError(f"지원하지 않는 파일 형식: {file_type}")


def _extract_pdf(file_path: str) -> list[dict]:
    # 참고: 폰트가 제대로 임베딩된 PDF(파워포인트/한글/워드에서 내보낸 강의자료 등)는
    # 정상 추출됨을 실제 샘플로 확인함. 스캔한 이미지 PDF는 텍스트 레이어가 없어서
    # extract_text()가 빈 문자열을 반환하므로 process_material()에서 별도 에러로 처리됨
    # (OCR은 미지원 — TODO).
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append({"page_or_slide_no": i, "text": text})
    return pages


def _extract_pptx(file_path: str) -> list[dict]:
    prs = Presentation(file_path)
    slides = []
    for i, slide in enumerate(prs.slides, start=1):
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    line = "".join(run.text for run in para.runs).strip()
                    if line:
                        parts.append(line)
        text = "\n".join(parts).strip()
        if text:
            slides.append({"page_or_slide_no": i, "text": text})
    return slides


# ---------- 2) 청크 분할 ----------
# 근거 출처(source_chunk_id -> page_or_slide_no)가 정확해야 하는 기능이라,
# 청크가 페이지/슬라이드 경계를 넘어가지 않게 한다 (안에서만 자른다).

def split_into_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        # 문단 하나가 이미 max_chars를 넘으면 문장 단위로 더 쪼갠다
        pieces = [para] if len(para) <= max_chars else _split_long_paragraph(para, max_chars)
        for piece in pieces:
            if current and len(current) + len(piece) + 2 > max_chars:
                chunks.append(current)
                current = piece
            else:
                current = f"{current}\n\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


def _split_long_paragraph(para: str, max_chars: int) -> list[str]:
    sentences = [s.strip() for s in para.replace("다. ", "다.\n").split("\n") if s.strip()]
    pieces: list[str] = []
    current = ""
    for s in sentences:
        if current and len(current) + len(s) + 1 > max_chars:
            pieces.append(current)
            current = s
        else:
            current = f"{current} {s}" if current else s
    if current:
        pieces.append(current)
    # 그래도 너무 길면(문장 구분이 안 되는 텍스트 등) 강제로 자른다
    final: list[str] = []
    for p in pieces:
        while len(p) > max_chars:
            final.append(p[:max_chars])
            p = p[max_chars:]
        if p:
            final.append(p)
    return final


def build_material_chunks(pages: list[dict]) -> list[dict]:
    """반환: [{"page_or_slide_no": int, "content": str}, ...]"""
    result = []
    for page in pages:
        for piece in split_into_chunks(page["text"]):
            result.append({"page_or_slide_no": page["page_or_slide_no"], "content": piece})
    return result


# ---------- 3) 임베딩 (스텁) ----------
# TODO: 임베딩 provider 확정되면 구현. 지금은 전부 None을 반환해서
# pgvector 컬럼은 비워두고, 벡터 검색 없이 "자료의 청크 전부"를 문제 생성에 쓴다
# (services/question_generation.py의 _select_chunks_for_material 참고).

def embed_chunks(texts: list[str]) -> list[list[float] | None]:
    if not texts:
        return []
    logger.warning("embed_chunks: 임베딩 provider가 아직 연결되지 않음 — 전부 None으로 저장")
    return [None] * len(texts)


# ---------- 4) 핵심 개념 추출 ----------

def extract_concepts(material_title: str, chunks: list[dict]) -> list[dict]:
    """chunks: [{"id": str, "content": str, "page_or_slide_no": int}, ...]
    반환: [{"name": str, "description": str, "parent": str}, ...]
    ANTHROPIC_API_KEY가 없으면 빈 리스트를 반환하고 경고만 남긴다 (파이프라인은 계속 진행).
    """
    if not settings.anthropic_api_key:
        logger.warning("extract_concepts: ANTHROPIC_API_KEY가 없어서 개념 추출을 건너뜀")
        return []

    from app.services.llm_client import call_with_tool_schema  # 순환 import 방지용 지연 import

    user_prompt = build_user_prompt(material_title, chunks)
    try:
        result = call_with_tool_schema(SYSTEM_PROMPT, user_prompt, CONCEPT_EXTRACTION_TOOL_SCHEMA)
    except Exception:
        logger.exception("extract_concepts: LLM 호출 실패")
        return []
    return result.get("concepts", [])


# ---------- 오케스트레이션 ----------

def process_material(db: Session, material: models.Material) -> None:
    """업로드된 자료 하나를 끝까지 처리. 실패하면 material.status를 failed로 남긴다.
    지금은 요청-응답 안에서 동기로 돈다 — 실제 서비스라면 큐(Celery/RQ 등)로 빼야 함 (TODO).
    """
    try:
        pages = extract_pages(material.file_path, material.file_type)
        if not pages:
            raise ValueError("자료에서 텍스트를 추출하지 못함 (스캔 이미지 PDF일 가능성 — OCR 미지원)")

        chunk_dicts = build_material_chunks(pages)
        embeddings = embed_chunks([c["content"] for c in chunk_dicts])

        chunk_rows: list[models.MaterialChunk] = []
        for c, emb in zip(chunk_dicts, embeddings):
            row = models.MaterialChunk(
                material_id=material.id,
                page_or_slide_no=c["page_or_slide_no"],
                content=c["content"],
                embedding=emb,
            )
            db.add(row)
            chunk_rows.append(row)
        db.flush()  # chunk_rows[i].id 확보

        concept_input = [
            {"id": str(r.id), "content": r.content, "page_or_slide_no": r.page_or_slide_no}
            for r in chunk_rows
        ]
        raw_concepts = extract_concepts(material.title, concept_input)

        name_to_id: dict[str, uuid.UUID] = {}
        for rc in raw_concepts:
            concept = models.Concept(
                material_id=material.id,
                name=rc["name"],
                description=rc.get("description"),
            )
            db.add(concept)
            db.flush()
            name_to_id[rc["name"]] = concept.id

        # 상위 개념 연결 (2차 패스 — 부모가 먼저 등장하지 않아도 되게)
        for rc in raw_concepts:
            parent_name = rc.get("parent")
            if parent_name and parent_name in name_to_id:
                child = db.query(models.Concept).get(name_to_id[rc["name"]])
                child.parent_concept_id = name_to_id[parent_name]

        material.status = "ready"
        db.commit()

    except Exception:
        logger.exception("process_material 실패 (material_id=%s)", material.id)
        material.status = "failed"
        db.commit()
