# QuizLoop (가제)

강의자료(PDF/PPT)를 업로드하면 AI가 문제를 생성하고, 학생이 푼 뒤 오답을 분석해서 취약 개념 위주로 다시 문제를 내주는 **폐루프(closed-loop) 학습 도구**.

- **대상**: 시험/과제를 준비하는 대학생
- **핵심 차별점**: 문제 생성에서 끝나지 않고 "생성 → 채점 → 오답분석 → 재출제"까지 자동으로 도는 것
- **상태**: 기획 문서 + 백엔드(FastAPI) + 프론트엔드(React) + ingestion/문제생성/채점/오답분석 파이프라인 + 로컬 Postgres(+pgvector) 엔드투엔드 테스트까지 완료. **인증(JWT), 스캔 이미지 PDF OCR, 백그라운드 큐(RQ+Redis), 오답 보기-개념 연결(v2), 벡터 유사도 청크 선택까지 전부 구현·검증 완료** (2026-09-14). 실서비스 배포 전 남은 건 실제 Voyage API 키 발급(계정 필요, 아래 "다음 액션" 13번 참고) 정도
- **용도**: 개인 사이드 프로젝트 / 포트폴리오

## 문서

- [기능명세서](docs/기능명세서.md)
- [DB 스키마](docs/DB스키마.md)
- [문제 생성 프롬프트 v1](docs/문제생성-프롬프트-v1.md)
- [오답 분석 프롬프트 v1](docs/오답분석-프롬프트-v1.md)
- [포트폴리오 포인트](docs/포트폴리오-포인트.md)

## 스택 (제안, 변경 가능)

| 영역 | 선택 |
|---|---|
| Backend | FastAPI |
| LLM | Claude / OpenAI API + RAG |
| DB | PostgreSQL |
| Frontend | React (MVP는 Streamlit도 고려) |
| 벡터 검색 | pgvector 또는 Chroma |

## 구조

```
quizloop/
├── README.md
├── docs/                       # 기획 문서
├── backend/                    # FastAPI (backend/README.md 참고)
│   ├── worker.py                # 백그라운드 큐(RQ) 워커 실행 스크립트
│   └── app/
│       ├── models.py, schemas.py, deps.py (인증 dependency)
│       ├── routers/            # auth, materials, quiz
│       ├── services/           # auth(JWT/bcrypt) / queue(RQ) / ingestion(+OCR) / 문제생성 / 채점 / 오답분석 / analysis
│       └── prompts/            # question_generation_v1.py(v2: 보기-개념 링크), concept_extraction_v1.py, wrong_answer_analysis_v1.py
└── frontend/                   # React + TS + Vite (frontend/README.md 참고)
    └── src/
        ├── auth/                # AuthContext (로그인 상태 전역 관리)
        ├── pages/               # Login / Signup / Materials / Quiz / Analysis / Regenerate / Settings
        ├── components/          # Sidebar, StatTile, WrongTypeBadge, Icons
        └── api/                 # client.ts(JWT 자동 첨부), types.ts
```

## 다음 액션

1. ~~DB 스키마 기준으로 SQLAlchemy 모델 작성~~ ✅
2. ~~문제 생성 프롬프트 v1 설계 (구조화 출력 JSON 스키마 고정)~~ ✅
3. ~~자료 업로드 → 청크 분할 → 개념추출 파이프라인 구현 (`ingestion` 서비스)~~ ✅ — PDF/PPTX 실제 샘플 파일로 추출/청크분할 테스트 완료 (페이지 경계 안 넘게 분할 확인)
4. ~~프론트엔드 실제 구현 (자료업로드/문제풀이/오답분석/재출제 페이지)~~ ✅ — `npm run build` 성공, `npm run lint` 통과
5. ~~로컬 PostgreSQL(+pgvector) 띄워서 업로드→생성→풀이→분석→재출제 전체 플로우 실제 엔드투엔드 테스트~~ ✅ (2026-09-14) — FastAPI TestClient + 실제 로컬 Postgres로 전체 플로우 검증 (LLM 호출만 mock). 이 과정에서 `weak_concept_stats` 신규 생성 시 `None + int` 에러 나는 실제 버그 발견·수정함
6. ~~임베딩 provider 선정 후 `embed_chunks()` 구현~~ ✅ (2026-09-14) — **Voyage AI (voyage-4, 1024차원)** 선정. Anthropic 공식 RAG 파트너, 다국어/한국어 지원, 계정당 2억 토큰 무료. `VOYAGE_API_KEY` 없으면 기존처럼 스텁(None)으로 그레이스풀 폴백 — 실제 키 넣기 전까지는 벡터 검색 없이 자료 전체 청크를 문제 생성에 사용
7. ~~스캔 이미지 PDF용 OCR 지원~~ ✅ (2026-09-14) — `pdf2image`(poppler) + `pytesseract`(tesseract + 한국어 언어팩)로, 텍스트 레이어가 없는 페이지만 골라서 OCR 시도. 합성 한글 스캔 이미지 PDF로 실제 동작 확인. 로컬(Windows) 설치 방법은 [backend/README.md](backend/README.md) 참고 — poppler/tesseract가 없으면 그 페이지만 조용히 스킵되고 나머지 파이프라인은 정상 동작
8. ~~`process_material`를 백그라운드 큐로 분리~~ ✅ (2026-09-14) — **RQ + Redis** 선택(Celery 대비 설정 단순). `worker.py`가 별도 프로세스로 실제 처리하고, Redis가 안 떠있으면 그 자리에서 동기로 폴백(추가 인프라 없이도 항상 동작). 업로드 응답이 `processing`으로 즉시 돌아오므로 프론트가 3초 간격으로 폴링해서 완료를 감지함
9. ~~오답 분석 프롬프트 정식 버전 설계~~ ✅ — `concept_confusion` 판단용으로 자료의 다른 개념 목록을 프롬프트에 포함, `call_with_tool_schema` 패턴으로 통일, 빈 답안은 LLM 호출 없이 즉시 `not_learned` 처리
10. ~~인증 붙이기~~ ✅ (2026-09-14) — JWT(PyJWT) + bcrypt로 직접 구현(passlib 없이, 의존성 최소화). `POST /auth/signup`, `/auth/login`, `GET /auth/me`. 모든 자료/문제 엔드포인트가 로그인 유저만 접근 가능하고, 소유권 체크(남의 자료/문제는 404로 통일해서 존재 자체를 숨김)까지 적용. 프론트엔드에 로그인/회원가입 페이지, 인증 컨텍스트, 토큰 자동 첨부까지 연결 완료
11. ~~`question_options`에 개념 연결 컬럼 추가~~ ✅ (2026-09-14, v2) — 오답분석 v1 문서의 "가장 큰 개선 포인트"였던 부분. 문제 생성 시점에 LLM이 각 보기가 어느 개념을 나타내는지(`related_concept`) 같이 표시하게 하고, 이를 `question_options.related_concept_id`로 저장. 오답분석 시 학생이 고른 오답 보기에 이 값이 있으면 **LLM 호출 없이 즉시 concept_confusion으로 판정** — 비용 절감 + 속도 개선 + 판정 일관성 향상
12. ~~교수님 시험 스타일 반영 개인화~~ ✅ (2026-09-14) — `materials.exam_style_note`(자유 텍스트, 업로드 시 또는 `PATCH /materials/{id}`로 설정)를 문제 생성 프롬프트가 형식/난이도 분포/표현 방식에 반영. "무엇을 묻는지"는 여전히 근거 자료로 제한 (프롬프트 규칙 8) — 프론트엔드 자료 업로드 화면에서도 메모 입력/수정 가능하게 연결함
13. 실제 Voyage API 키로 임베딩 발급 후 벡터 유사도 기반 청크 선택(`_select_chunks_for_material`)으로 교체 — **코드는 완성**(대상 개념명을 질의로 임베딩해서 pgvector 코사인 유사도 순으로 관련 청크만 추리고, 임베딩 없는 자료는 자동으로 "전체 청크" 방식 폴백). 다만 실제 활성화는 [dash.voyageai.com](https://dash.voyageai.com)에서 API 키를 발급받아 `.env`의 `VOYAGE_API_KEY`에 넣어야 함 — 이건 본인 계정 가입이 필요해서 AI가 대신 해줄 수 없는 부분
