# QuizLoop

강의자료(PDF/PPT)를 올리면 AI가 문제를 만들어주고, 풀고 나면 오답을 분석해서 어떤 개념이 약한지 찾아주는 학습 도구. 문제만 뽑아주고 끝나는 게 아니라 생성 → 채점 → 오답분석 → 재출제까지 자동으로 도는 게 포인트.

개인 사이드 프로젝트 / 포트폴리오용으로 만들고 있음.

## 어떻게 동작하냐면

1. PDF/PPT 업로드하면 텍스트 추출하고 청크로 쪼갬 (텍스트 레이어 없는 스캔본이면 OCR도 돌림)
2. 청크에서 개념을 뽑고, 그 개념들 기준으로 문제를 생성 — 근거 없는 문제를 안 내려고 RAG로 grounding 걸어둠
3. 풀고 나면 채점하고, 틀린 문제는 "단순 실수 / 개념 혼동 / 아예 안 배운 것" 중 어디에 해당하는지 분류
4. 취약한 개념 위주로 재출제

## 스택

- 백엔드: FastAPI, SQLAlchemy, PostgreSQL(+pgvector), RQ(Redis Queue), PyJWT + bcrypt
- AI: Claude API(구조화 출력 강제), Voyage AI 임베딩
- 프론트엔드: React, TypeScript, Vite

## 구조
quizloop/
├── docs/ # 기획 문서
├── backend/ # FastAPI (자세한 건 backend/README.md 참고)
└── frontend/ # React + TS + Vite


## 지금 상태

백엔드/프론트엔드 다 돌아가고, 인증(JWT), 스캔 PDF OCR, 백그라운드 처리(RQ+Redis), 오답분석 최적화(문제 생성 시점에 보기-개념을 미리 연결해서 오답 낼 때마다 LLM 부르지 않게 함)까지 구현했고 로컬 Postgres로 엔드투엔드 테스트도 돌려봄. 이 과정에서 실제 버그(`weak_concept_stats` 생성 시 `TypeError: NoneType + int`)도 하나 잡음.

남은 건:
- Voyage API 키 발급받아서 벡터 유사도 기반 청크 선택 실제로 켜기 (코드는 이미 완성, 키만 넣으면 됨)
- Alembic으로 DB 마이그레이션 정리
- 단답형 채점을 문자열 완전일치 말고 LLM 기반 유사도 채점으로 바꾸기

## 문서

- [기능명세서](docs/기능명세서.md)
- [DB 스키마](docs/DB스키마.md)
- [문제 생성 프롬프트 v1](docs/문제생성-프롬프트-v1.md)
- [오답 분석 프롬프트 v1](docs/오답분석-프롬프트-v1.md)
- [포트폴리오 포인트](docs/포트폴리오-포인트.md)
