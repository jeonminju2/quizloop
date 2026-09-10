"""자료 업로드 엔드포인트."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.services.ingestion import process_material

router = APIRouter(prefix="/materials", tags=["materials"])

ALLOWED_EXTENSIONS = {"pdf", "ppt", "pptx"}


@router.post("/upload", response_model=schemas.MaterialOut)
async def upload_material(
    file: UploadFile,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: .{ext}")

    material = models.Material(
        user_id=user_id,
        title=file.filename,
        file_type=ext,
        file_path="",  # 아래에서 실제 저장 경로로 채움
        status="uploaded",
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

    # MVP: 요청 안에서 동기로 처리. 자료가 커지면 백그라운드 큐로 옮길 것 (TODO).
    process_material(db, material)
    db.refresh(material)

    return material


@router.get("", response_model=list[schemas.MaterialOut])
def list_materials(user_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(models.Material)
        .filter(models.Material.user_id == user_id)
        .order_by(models.Material.created_at.desc())
        .all()
    )


@router.get("/{material_id}", response_model=schemas.MaterialOut)
def get_material(material_id: uuid.UUID, db: Session = Depends(get_db)):
    material = db.query(models.Material).get(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="자료를 찾을 수 없음")
    return material
