from fastapi import FastAPI
from app.api.routes.users import router as users_router
from app.api.routes.auth import router as auth_router
from app.api.routes.calendar import router as calendar_router
from app.api.routes.timetable import router as timetable_router

app = FastAPI(title="InovAulas API", version="0.1.0")

app.include_router(users_router)
app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(timetable_router)

@app.get("/health")
def health():
    return {"status": "ok"}