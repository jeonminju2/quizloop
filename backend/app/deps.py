"""라우터 간 공유하는 FastAPI dependency. 순환 import 방지용으로 별도 파일로 뺌."""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.services.auth import decode_access_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")

    token = authorization.split(" ", 1)[1].strip()
    try:
        user_id = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 토큰입니다")

    user = db.query(models.User).get(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")
    return user
