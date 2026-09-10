# QuizLoop Backend (FastAPI 스캐폴드)

기능명세서(`../docs/기능명세서.md`)·DB스키마(`../docs/DB스키마.md`) 기준으로 만든 기본 구조. 아직 실행 가능한 완제품은 아니고, 구조/모델/프롬프트/엔드포인트 뼈대만 잡아둔 상태.

## 실행 준비

```bash
python -m venv venv
source venv/bin/activate   # Windows는 venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 값 채우기 (DB_URL, ANTHROPIC_API_KEY 등)
```

PostgreSQL에 `pgvector` 익스텐션 설치 필요:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 구조

```
app/
├── main.py              # FastAPI 앱 엔트리
├── config.py             # 환경변수 설정
├── database.py           # SQLAlchemy 엔진/세션
├── models.py              # ORM 모델 (DB스키마.md 그대로 반영)
├── schemas.py             # API 요청/응답 Pydantic 스키마
├── routers/
│   ├── materials.py       # 자료 업로드
│   └── quiz.py            # 문제 생성/제출/재출제
├── services/
│   ├── llm_client.py               # Anthropic API 래퍼 (tool_choice로 구조화 출력 강제)
│   ├── question_generation.py      # 문제 생성 오케스트레이션
│   ├── grading.py                   # 채점
│   └── wrong_answer_analysis.py     # 오답 분류 + 취약개념 집계
└── prompts/
    └── question_generation_v1.py   # 문제 생성 프롬프트 v1 (설계 문서: ../docs/문제생성-프롬프트-v1.md)
```

## 아직 안 만든 것 (다음 작업 후보)

- [ ] `ingestion` 서비스: PDF/PPT 텍스트 추출 → 청크 분할 → 임베딩 → 핵심 개념 추출
- [ ] DB 마이그레이션 (Alembic)
- [ ] 단답형 채점을 LLM 기반 유사도 채점으로 교체
- [ ] 오답 분석 프롬프트 별도 버전 설계 (`wrong_answer_analysis.py`는 지금 최소 버전)
- [ ] 인증/인가 (지금은 user_id를 쿼리 파라미터로 그냥 받음 — 데모용)
- [ ] 프론트엔드
