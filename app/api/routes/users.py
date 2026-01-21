from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.schemas import UserCreate, UserOut, UserUpdate
from app.api.deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.execute(select(User).order_by(User.id)).scalars().all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    exists = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="username already exists")

    user = User(username=payload.username, full_name=payload.full_name, role=payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    db.delete(user)
    db.commit()
    return None