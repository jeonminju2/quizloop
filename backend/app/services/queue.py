"""자료 처리(process_material)를 백그라운드 큐(RQ + Redis)로 넘기는 어댑터.

업로드 요청 핸들러(routers/materials.py)는 여기 enqueue_process_material()만 호출한다.
Redis/워커가 떠있으면 실제로 큐에 job이 들어가서 별도 워커 프로세스(worker.py)가 처리하고,
업로드 응답은 material.status="processing" 상태로 즉시 돌아간다 — 프론트는 자료 목록을
주기적으로 다시 불러와서 "ready"로 바뀌는 걸 감지한다 (frontend/src/pages/MaterialsPage.tsx).

Redis에 연결이 안 되면(로컬에서 워커를 안 띄워놓은 경우 등) 그 자리에서 동기로 즉시 처리하도록
폴백한다 — 큐 인프라 없이도 앱 자체는 계속 동작하게 하기 위함. 단 이 경우 업로드 요청이
실제 처리 시간만큼 느려진다 (원래 MVP 동작과 동일).
"""

import logging
import uuid

from redis import Redis
from rq import Queue

from app.config import settings

logger = logging.getLogger(__name__)

QUEUE_NAME = "quizloop-materials"

_redis_conn: Redis | None = None
_queue: Queue | None = None


def _get_queue() -> Queue:
    global _redis_conn, _queue
    if _queue is None:
        _redis_conn = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        _redis_conn.ping()  # 여기서 바로 연결 확인 — 실패하면 예외를 던져서 폴백 경로를 타게 함
        _queue = Queue(QUEUE_NAME, connection=_redis_conn)
    return _queue


def process_material_job(material_id: str) -> None:
    """워커 프로세스(worker.py)가 실행하는 실제 job. DB 세션은 여기서 새로 연다 —
    워커는 요청과 분리된 별도 프로세스라 request-scoped 세션을 공유할 수 없다."""
    from app import models
    from app.database import SessionLocal
    from app.services.ingestion import process_material

    db = SessionLocal()
    try:
        material = db.query(models.Material).get(uuid.UUID(material_id))
        if material is None:
            logger.warning("process_material_job: material %s를 찾을 수 없음", material_id)
            return
        process_material(db, material)
    finally:
        db.close()


def _process_synchronously(material_id: uuid.UUID) -> None:
    from app import models
    from app.database import SessionLocal
    from app.services.ingestion import process_material

    db = SessionLocal()
    try:
        material = db.query(models.Material).get(material_id)
        if material is not None:
            process_material(db, material)
    finally:
        db.close()


def enqueue_process_material(material_id: uuid.UUID) -> None:
    try:
        queue = _get_queue()
        queue.enqueue(process_material_job, str(material_id), job_timeout=600)
        logger.info("material %s 처리를 백그라운드 큐(%s)에 등록함", material_id, QUEUE_NAME)
    except Exception:
        global _queue  # 다음 요청에서 재연결을 다시 시도하도록 캐시를 비움
        _queue = None
        logger.warning(
            "Redis 큐(%s)에 연결할 수 없어서 material %s를 동기로 즉시 처리함 "
            "(워커가 안 떠있거나 Redis가 안 켜져 있는 것으로 보임)",
            settings.redis_url,
            material_id,
            exc_info=True,
        )
        _process_synchronously(material_id)
