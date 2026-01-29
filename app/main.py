import os
from fastapi import FastAPI
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User  # ajuste pro nome real do seu model

from app.api.routes.users import router as users_router
from app.api.routes.auth import router as auth_router
from app.api.routes.calendar import router as calendar_router
from app.api.routes.timetable import router as timetable_router

app = FastAPI(title="InovAulas API", version="0.1.0")

app.include_router(users_router)
app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(timetable_router)

@app.on_event("startup")
def ensure_bootstrap_user():
    username = os.getenv("LOGIN_USERNAME", "paulo").strip()
    if not username:
        return

    db = SessionLocal()
    try:
        u = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if not u:
            db.add(User(username=username))
            db.commit()
            print(f"[BOOTSTRAP] User criado: {username}")
        else:
            print(f"[BOOTSTRAP] User OK: {username}")
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}