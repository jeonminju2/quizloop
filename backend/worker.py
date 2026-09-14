"""백그라운드 워커 실행 스크립트.

사용법: 백엔드 루트에서 `python worker.py` (Redis가 REDIS_URL에 떠있어야 함, 기본 redis://localhost:6379/0).
업로드된 자료의 텍스트추출/청크분할/개념추출(process_material)을 여기서 실제로 처리한다.
FastAPI 서버 프로세스와는 별개로 띄워야 함 — uvicorn 프로세스와 worker.py 프로세스 둘 다 실행.

로컬 개발 예시:
    # 터미널 1
    redis-server
    # 터미널 2
    uvicorn app.main:app --reload
    # 터미널 3
    python worker.py
"""

from redis import Redis
from rq import Worker

from app.config import settings
from app.services.queue import QUEUE_NAME

if __name__ == "__main__":
    conn = Redis.from_url(settings.redis_url)
    worker = Worker([QUEUE_NAME], connection=conn)
    print(f"QuizLoop 백그라운드 워커 시작 — queue={QUEUE_NAME}, redis={settings.redis_url}")
    worker.work()
