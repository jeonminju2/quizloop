"""회원가입/로그인 (JWT). 기존 라우터들은 더 이상 user_id를 쿼리파라미터로 안 받고
Authorization: Bearer <token> 헤더에서 현재 유저를 가져온다 (app/deps.py의 get_current_user).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.TokenOut)
def signup(req: schemas.SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == req.email).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다")

    user = models.User(email=req.email, name=req.name, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=schemas.TokenOut)
def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if user is None or not user.password_hash or not verify_password(req.password, user.password_hash):
        # 이메일 존재 여부를 흘리지 않으려고 두 실패 케이스에 동일한 메시지/상태코드 사용
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")
    return schemas.TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
