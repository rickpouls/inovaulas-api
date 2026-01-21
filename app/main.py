from fastapi import FastAPI
from app.api.routes.users import router as users_router

app = FastAPI(title="InovAulas API", version="0.1.0")

app.include_router(users_router)

@app.get("/health")
def health():
    return {"status": "ok"}