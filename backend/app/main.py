from fastapi import FastAPI

from app.routers import materials, quiz

app = FastAPI(title="QuizLoop API", version="0.1.0")

app.include_router(materials.router)
app.include_router(quiz.router)


@app.get("/health")
def health():
    return {"status": "ok"}
