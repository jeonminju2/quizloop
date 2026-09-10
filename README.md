# QuizLoop (가제)

강의자료(PDF/PPT)를 업로드하면 AI가 문제를 생성하고, 학생이 푼 뒤 오답을 분석해서 취약 개념 위주로 다시 문제를 내주는 **폐루프(closed-loop) 학습 도구**.

- **대상**: 시험/과제를 준비하는 대학생
- **핵심 차별점**: 문제 생성에서 끝나지 않고 "생성 → 채점 → 오답분석 → 재출제"까지 자동으로 도는 것
- **상태**: 기획 문서 + 백엔드(FastAPI) + 프론트엔드(React) + 자료 업로드/청크분할/개념추출 파이프라인까지 구현 완료. 로컬 Postgres 붙여서 엔드투엔드 테스트하는 것만 남음
- **용도**: 개인 사이드 프로젝트 / 포트폴리오

## 문서

- [기능명세서](docs/기능명세서.md)
- [DB 스키마](docs/DB스키마.md)
- [문제 생성 프롬프트 v1](docs/문제생성-프롬프트-v1.md)
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
│   └── app/
│       ├── models.py, schemas.py
│       ├── routers/            # materials, quiz
│       ├── services/           # ingestion / 문제생성 / 채점 / 오답분석 / analysis
│       └── prompts/            # question_generation_v1.py, concept_extraction_v1.py
└── frontend/                   # React + TS + Vite (frontend/README.md 참고)
    └── src/
        ├── pages/               # Materials / Quiz / Analysis / Regenerate / Settings
        ├── components/          # Sidebar, StatTile, WrongTypeBadge, Icons
        └── api/                 # client.ts, types.ts
```

## 다음 액션

1. ~~DB 스키마 기준으로 SQLAlchemy 모델 작성~~ ✅
2. ~~문제 생성 프롬프트 v1 설계 (구조화 출력 JSON 스키마 고정)~~ ✅
3. ~~자료 업로드 → 청크 분할 → 개념추출 파이프라인 구현 (`ingestion` 서비스)~~ ✅ — PDF/PPTX 실제 샘플 파일로 추출/청크분할 테스트 완료 (페이지 경계 안 넘게 분할 확인)
4. ~~프론트엔드 실제 구현 (자료업로드/문제풀이/오답분석/재출제 페이지)~~ ✅ — `npm run build` 성공, `npm run lint` 통과
5. 로컬 PostgreSQL(+pgvector) 띄워서 업로드→생성→풀이→분석→재출제 전체 플로우 실제 엔드투엔드 테스트
6. 임베딩 provider 선정 후 `ingestion.py`의 `embed_chunks()` 구현 (지금은 스텁 — 벡터 검색 없이 자료 전체 청크를 문제 생성에 사용 중)
7. 스캔 이미지 PDF용 OCR 지원 (지금은 텍스트 레이어 없으면 실패 처리)
8. `process_material`를 백그라운드 큐(Celery/RQ 등)로 분리 (지금은 업로드 요청 안에서 동기 처리)
9. 오답 분석 프롬프트 정식 버전 설계 (`wrong_answer_analysis.py`는 지금 최소 버전)
10. 인증 붙이기 (지금은 `DEMO_USER_ID` 고정값으로 대체 중)
