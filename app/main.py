from fastapi import FastAPI

app = FastAPI(title="InovAulas API")

@app.get("/health")
def health():
    return {"status": "ok"}