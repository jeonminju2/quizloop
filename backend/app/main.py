from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, materials, quiz

app = FastAPI(title="QuizLoop API", version="0.1.0")

# 프론트(Vite 개발서버, 기본 5173)에서 다른 origin(8000)으로 호출하니까 CORS 허용 필요.
# 배포 시엔 allow_origins를 실제 프론트 도메인으로 좁힐 것 (지금은 개발 편의상 전체 허용).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # allow_origins=["*"]와 함께 credentials=True는 브라우저가 거부함
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(materials.router)
app.include_router(quiz.router)


@app.get("/health")
def health():
    return {"status": "ok"}
