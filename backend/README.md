# QuizLoop Backend (FastAPI)

강의자료 업로드 → 청크분할/개념추출 → 문제생성 → 채점 → 오답분석 → 재출제까지 도는 백엔드.
인증(JWT), 스캔 이미지 PDF OCR, 백그라운드 큐(RQ+Redis), 오답 보기-개념 연결(v2), pgvector
벡터 유사도 청크 선택까지 구현되어 있다.

## 실행 준비

```bash
python -m venv venv
source venv/bin/activate   # Windows는 venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 값 채우고 시작 (아래 "필수 환경변수" 참고)
```

PostgreSQL에 `pgvector` 익스텐션 설치 필요:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 필수 환경변수 (`.env`)

- `DATABASE_URL` — Postgres 접속 문자열
- `ANTHROPIC_API_KEY` — 문제생성/개념추출/오답분석에 사용 (없으면 개념추출/문제생성이 빈 결과로 그레이스풀 스킵됨)
- `JWT_SECRET` — **반드시 설정할 것.** 비워두면 프로세스 시작마다 랜덤 시크릿이 생성돼서 서버
  재시작할 때마다 기존 로그인 토큰이 전부 무효화된다. `python -c "import secrets; print(secrets.token_urlsafe(32))"`로 생성
- `VOYAGE_API_KEY` — (선택) 없으면 임베딩 없이 "자료 전체 청크"를 문제 생성에 사용. 있으면
  벡터 유사도 기반으로 관련 청크만 추림. [dash.voyageai.com](https://dash.voyageai.com)에서 발급 (계정당 2억 토큰 무료)
- `REDIS_URL` — (선택) 없거나 Redis가 안 떠있으면 자동으로 동기 처리 폴백 (앱 자체는 계속 동작)

## 실행

로컬 개발은 터미널 3개:

```bash
# 터미널 1 — Redis (백그라운드 큐용, 없어도 동기 폴백으로 동작은 함)
redis-server

# 터미널 2 — API 서버
uvicorn app.main:app --reload

# 터미널 3 — 백그라운드 워커 (업로드된 자료의 텍스트추출/개념추출을 실제로 처리)
python worker.py
```

## 스캔 이미지 PDF OCR 설치 (Windows)

텍스트 레이어가 없는 PDF(스캔본)는 OCR로 자동 폴백되는데, 아래 두 가지가 시스템에 설치되어
있어야 동작한다 (`requirements.txt`의 `pdf2image`/`pytesseract`는 파이썬 래퍼일 뿐, 실제
엔진은 별도 설치 필요):

1. **Tesseract**: [UB Mannheim 빌드](https://github.com/UB-Mannheim/tesseract/wiki) 설치 —
   설치 마법사에서 **Additional language data > Korean** 꼭 체크. 설치 후 `tesseract.exe`가
   있는 폴더(보통 `C:\Program Files\Tesseract-OCR`)를 시스템 PATH에 추가.
2. **poppler**: [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) 다운로드 →
   압축 풀고 `Library\bin` 폴더를 PATH에 추가 (`pdftoppm.exe`가 그 안에 있어야 함).

둘 중 하나라도 없으면 해당 페이지만 조용히 스킵되고(로그에 경고만 남음) 나머지 파이프라인은
정상 동작한다 — 텍스트 레이어가 있는 일반 PDF/PPT는 이 설치 없이도 항상 잘 된다.

## 구조

```
app/
├── main.py                          # FastAPI 앱 엔트리 (CORS 포함)
├── config.py                        # 환경변수 설정
├── database.py                      # SQLAlchemy 엔진/세션
├── deps.py                          # get_current_user (JWT Authorization 헤더 검증)
├── models.py                        # ORM 모델 (DB스키마.md 반영 + v2: QuestionOption.related_concept_id)
├── schemas.py                       # API 요청/응답 Pydantic 스키마
├── routers/
│   ├── auth.py                      # 회원가입/로그인/내 정보
│   ├── materials.py                 # 자료 업로드 (백그라운드 큐로 처리 위임)
│   └── quiz.py                      # 문제 생성/제출/재출제/오답분석 (전부 소유권 체크)
├── services/
│   ├── auth.py                      # bcrypt 해시 + JWT 발급/검증
│   ├── queue.py                     # RQ 큐 어댑터 (Redis 없으면 동기 폴백)
│   ├── llm_client.py                # Anthropic API 래퍼 (tool_choice로 구조화 출력 강제)
│   ├── ingestion.py                 # 텍스트추출(+OCR)/청크분할/임베딩(Voyage)/개념추출
│   ├── question_generation.py       # 문제 생성 오케스트레이션 (벡터 유사도 청크 선택 포함)
│   ├── grading.py                   # 채점
│   ├── wrong_answer_analysis.py     # 오답 분류(v2: 즉시판정 경로 포함) + 취약개념 집계
│   └── analysis.py                  # 오답분석 대시보드용 집계
└── prompts/
    ├── question_generation_v1.py    # 문제 생성 프롬프트 (v2: 보기-개념 링크 스키마 포함)
    ├── concept_extraction_v1.py
    └── wrong_answer_analysis_v1.py

worker.py                            # 백그라운드 큐 워커 실행 스크립트 (uvicorn과 별도 프로세스)
```

## 테스트

`tests/e2e_test.py` — 실제 로컬 Postgres(+pgvector)에 스키마를 새로 만들고, FastAPI
TestClient로 회원가입→로그인→자료업로드→문제생성→채점→오답분석→재출제까지 전체 플로우를
태우는 엔드투엔드 테스트. LLM 호출만 monkeypatch로 대체(비용/키 없이 실행 가능)하고 나머지는
전부 실제 코드 경로.

```bash
# 사전조건: 로컬에 Postgres(5432, postgres/postgres, quizloop DB)가 떠있어야 함.
python tests/e2e_test.py
```

## 남은 것

- [ ] 실제 Voyage API 키 발급 후 벡터 유사도 청크 선택 활성화 (코드는 완성, 본인 계정 가입만 남음)
- [ ] DB 마이그레이션 (Alembic) — 지금은 `Base.metadata.create_all`로 스키마 생성
- [ ] 단답형 채점을 LLM 기반 유사도 채점으로 교체 (지금은 문자열 완전 일치)
- [ ] 배포 시 CORS `allow_origins`를 실제 프론트 도메인으로 좁히기 (지금은 개발 편의상 전체 허용)
