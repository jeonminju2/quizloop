"""자료 업로드 엔드포인트."""

import os
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.services.ingestion import process_material

router = APIRouter(prefix="/materials", tags=["materials"])

ALLOWED_EXTENSIONS = {"pdf", "ppt", "pptx"}


def _get_owned_material(db: Session, material_id: uuid.UUID, user: models.User) -> models.Material:
    material = db.query(models.Material).get(material_id)
    if material is None or material.user_id != user.id:
        # 존재하지만 남의 자료인 경우도 404로 통일 — "존재는 하는데 권한이 없다"를 노출하지 않음
        raise HTTPException(status_code=404, detail="자료를 찾을 수 없음")
    return material


@router.post("/upload", response_model=schemas.MaterialOut)
async def upload_material(
    file: UploadFile,
    exam_style_note: str | None = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: .{ext}")

    material = models.Material(
        user_id=current_user.id,
        title=file.filename,
        file_type=ext,
        file_path="",  # 아래에서 실제 저장 경로로 채움
        status="uploaded",
        exam_style_note=(exam_style_note or "").strip() or None,
    )
    db.add(material)
    db.flush()  # material.id 확보

    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, f"{material.id}.{ext}")
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    material.file_path = file_path
    material.status = "processing"
    db.commit()
    db.refresh(material)

    # 자료 처리(텍스트추출/청크/개념추출)는 백그라운드 큐(RQ)로 넘긴다 — services/queue.py 참고.
    # Redis가 안 떠있으면(로컬 개발 중 등) 그 자리에서 동기로 폴백 처리한다.
    from app.services.queue import enqueue_process_material

    enqueue_process_material(material.id)
    db.refresh(material)

    return material


@router.get("", response_model=list[schemas.MaterialOut])
def list_materials(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(models.Material)
        .filter(models.Material.user_id == current_user.id)
        .order_by(models.Material.created_at.desc())
        .all()
    )


@router.get("/{material_id}", response_model=schemas.MaterialOut)
def get_material(
    material_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_material(db, material_id, current_user)


@router.patch("/{material_id}", response_model=schemas.MaterialOut)
def update_material(
    material_id: uuid.UUID,
    req: schemas.MaterialUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """업로드 이후에도 시험 스타일 메모를 자유롭게 추가/수정할 수 있게 하는 엔드포인트."""
    material = _get_owned_material(db, material_id, current_user)
    if req.exam_style_note is not None:
        material.exam_style_note = req.exam_style_note.strip() or None
    db.commit()
    db.refresh(material)
    return material
