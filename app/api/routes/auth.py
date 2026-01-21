import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginIn, LoginOut
from app.core.security import sign
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

def _secret() -> str:
    return settings.AUTH_SECRET

@router.post("/login", response_model=LoginOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    token = sign(
        {"sub": user.username, "role": user.role},
        secret=_secret(),
        ttl_seconds=60 * 60 * 24 * 7,  # 7 dias
    )
    return LoginOut(access_token=token)