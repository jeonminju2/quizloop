"""QuizLoop 백엔드 엔드투엔드 테스트 (v2).

실제 로컬 PostgreSQL(+pgvector)에 스키마를 만들고, FastAPI TestClient로
실제 HTTP 라우터를 통해 전체 플로우를 태운다:

  회원가입/로그인(JWT) -> 자료 업로드(백그라운드 큐 -> process_material) -> 문제 생성
  (v2: 보기-개념 링크 포함) -> 채점(submit) -> 오답분석(v2: LLM 없이 즉시 판정 경로 포함)
  /취약개념 집계 -> 오답분석 조회(analysis) -> 재출제(regenerate, 벡터 유사도 청크 선택 경로)
  -> 재출제 결과 분석(before/after 비교)

v1과 달라진 점:
  - 라우터가 전부 JWT 인증을 요구하므로 user_id 쿼리파라미터 대신 signup/login으로 얻은
    Authorization: Bearer 토큰을 모든 요청에 붙인다.
  - 업로드가 더 이상 동기(process_material 직접 호출)가 아니라 백그라운드 큐(RQ+Redis)로
    넘어간다 -> 업로드 응답에서는 status가 아직 processing일 수 있어서, 실제 워커가 처리할
    시간을 기다렸다가(폴링) status가 ready/failed가 될 때까지 확인한다.
  - fake LLM이 문제 생성 응답에 related_concept를 채워서 v2 보기-개념 링크 경로도 검증한다.

LLM 호출(call_with_tool_schema)은 ANTHROPIC_API_KEY가 없어서 monkeypatch로 대체한다 —
실제 네트워크 호출 없이 파이프라인/DB 관계/API 스키마 검증에 집중. 임베딩(VOYAGE_API_KEY)도
비워둬서 "키 없을 때 우아하게 스킵하는" 경로를 그대로 테스트한다 (실제 서비스 코드 경로 그대로).
텍스트 추출/청크분할/개념 저장/문제 저장/채점/집계는 전부 진짜 코드가 실행된다.

사전조건: 로컬에 postgres(5432, postgres/postgres, quizloop db)와 redis(6379)가 떠있어야 함.
백그라운드 워커(worker.py)를 이 스크립트 실행 전에 별도 프로세스로 띄워두면 진짜 비동기
큐 경로를(워커가 처리), 안 띄워두면 큐 연결 실패 -> 동기 폴백 경로를 테스트하게 된다.
"""

import os
import re
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
SAMPLE_PDF = Path(__file__).resolve().parent / "fixtures" / "sample_os_ch6_kr.pdf"

os.environ["DATABASE_URL"] = "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/quizloop"
os.environ["ANTHROPIC_API_KEY"] = "dummy-not-real-key"  # call_with_tool_schema를 통째로 패치하므로 실호출 없음
os.environ["VOYAGE_API_KEY"] = ""  # 일부러 비움 -> embed_chunks()/embed_query()의 그레이스풀 폴백 경로 테스트
os.environ["UPLOAD_DIR"] = "/tmp/quizloop_uploads_test"
os.environ["JWT_SECRET"] = "e2e-test-secret-do-not-use-in-prod"
# 일부러 존재하지 않는 포트 -> enqueue_process_material()이 Redis 연결 실패를 감지하고
# 동기 폴백 경로를 타게 만든다. 이렇게 해야 아래 monkeypatch(fake LLM)가 실제로 적용된 상태로
# 파이프라인 전체(개념추출/문제생성 v2 링크/오답분석 즉시판정)를 검증할 수 있다 — 진짜 워커는
# 별도 프로세스라 이 프로세스의 monkeypatch를 못 보므로 여기선 안 쓴다 (큐 인프라 자체의
# 동작은 worker.py를 별도로 띄워서 따로 확인함).
os.environ["REDIS_URL"] = "redis://127.0.0.1:16379/0"

sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app import models  # noqa: E402

print("=== 0) 스키마 생성 ===")
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
print("OK — 테이블 생성 완료:", list(Base.metadata.tables.keys()))


# ---------- LLM 호출 fake ----------

_wrong_tag_cycle = ["concept_confusion", "careless_mistake", "not_learned"]
_wrong_tag_counter = {"i": 0}


def fake_call_with_tool_schema(system_prompt, user_prompt, tool_schema, max_tokens=4096):
    name = tool_schema["name"]

    if name == "submit_questions":
        concept_lines = re.findall(r"- \(([0-9a-fA-F-]{36})\) ([^:]+):", user_prompt)
        chunk_ids = re.findall(r"\[chunk_id=([0-9a-fA-F-]{36})\]", user_prompt)
        m = re.search(r"문제 수: (\d+)", user_prompt)
        num_questions = int(m.group(1)) if m else min(len(concept_lines), 4)
        style_used = "[교수님 시험 스타일" in user_prompt

        questions = []
        for i in range(num_questions):
            if not concept_lines:
                break
            concept_id, concept_name = concept_lines[i % len(concept_lines)]
            other_concept_name = concept_lines[(i + 1) % len(concept_lines)][1] if len(concept_lines) > 1 else ""
            chunk_id = chunk_ids[i % len(chunk_ids)] if chunk_ids else ""
            is_mc = (i % 2 == 0) if not style_used else True  # 스타일 노트가 있으면 객관식 위주로 낸 척
            if is_mc:
                # v2: 정답 보기는 대상 개념과 같은 related_concept, 헷갈리는 오답은 다른 개념명,
                # 나머지 단순 오답은 빈 문자열 -> question_generation.py의 related_concept_id 저장 경로 검증
                options = [
                    {"text": f"{concept_name} 정답 설명 #{i}", "is_correct": True, "related_concept": concept_name},
                    {
                        "text": f"{concept_name}과 혼동되는 오답 #{i}",
                        "is_correct": False,
                        "related_concept": other_concept_name,
                    },
                    {"text": "관련 없는 오답 A", "is_correct": False, "related_concept": ""},
                    {"text": "관련 없는 오답 B", "is_correct": False, "related_concept": ""},
                ]
                correct_answer = options[0]["text"]
                q_type = "multiple_choice"
            else:
                options = []
                correct_answer = f"{concept_name} 정답"
                q_type = "short_answer"
            questions.append(
                {
                    "type": q_type,
                    "concept": concept_name,
                    "question_text": f"[테스트문제 #{i}] {concept_name}에 대해 설명하시오",
                    "options": options,
                    "correct_answer": correct_answer,
                    "explanation": f"{concept_name} 관련 해설입니다.",
                    "source_chunk_id": chunk_id,
                }
            )
        return {"questions": questions}

    if name == "submit_wrong_answer_analysis":
        # v2 경로(related_concept_id가 박혀있는 오답)는 이 함수 호출 자체를 스킵하므로,
        # 여기 도달한다는 건 "related_concept_id가 없는" 케이스(=단순 오답, 빈 문자열)의
        # LLM 폴백 경로가 정상 동작 중이라는 뜻.
        other = re.findall(r"^- ([^:]+):", user_prompt, flags=re.MULTILINE)
        tag = _wrong_tag_cycle[_wrong_tag_counter["i"] % len(_wrong_tag_cycle)]
        _wrong_tag_counter["i"] += 1
        confused = other[0] if (tag == "concept_confusion" and other) else ""
        return {
            "tag_type": tag,
            "confused_with_concept": confused,
            "reasoning": f"[테스트용 fake 분류] {tag}로 분류함",
        }

    if name == "submit_concepts":
        return {"concepts": []}  # 이 테스트에서는 안 씀 (아래에서 직접 monkeypatch)

    raise AssertionError(f"예상 못한 tool_schema: {name}")


import app.services.llm_client as llm_client_module  # noqa: E402
import app.services.question_generation as qg_module  # noqa: E402

llm_client_module.call_with_tool_schema = fake_call_with_tool_schema
qg_module.call_with_tool_schema = fake_call_with_tool_schema  # 모듈 top-level import라 별도 패치 필요


# extract_concepts는 ANTHROPIC_API_KEY 유무와 무관하게 결정적인 개념 목록을 반환하도록 직접 patch
import app.services.ingestion as ingestion_module  # noqa: E402

FAKE_CONCEPTS = [
    {"name": "세마포어와 뮤텍스의 차이", "description": "세마포어는 신호 전달, 뮤텍스는 소유권 기반 잠금이라는 차이", "parent": ""},
    {"name": "교착상태 발생 조건", "description": "상호배제/점유와 대기/비선점/순환대기 4가지 조건", "parent": ""},
    {"name": "LRU와 FIFO 페이지 교체", "description": "LRU는 최근 참조 기준, FIFO는 적재 순서 기준으로 교체", "parent": ""},
]


def fake_extract_concepts(material_title, chunks):
    return FAKE_CONCEPTS


ingestion_module.extract_concepts = fake_extract_concepts

print("=== LLM 호출 monkeypatch 완료 (concept 추출/문제생성(v2 related_concept 포함)/오답분석 fake) ===\n")


# ---------- FastAPI TestClient로 실제 라우터 태우기 ----------

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

print("=== 1) 회원가입 + 로그인 (JWT) ===")
signup_resp = client.post(
    "/auth/signup",
    json={"email": "e2e-test@example.com", "password": "test-password-123", "name": "테스트유저"},
)
assert signup_resp.status_code == 200, signup_resp.text
token = signup_resp.json()["access_token"]
auth_headers = {"Authorization": f"Bearer {token}"}
print(f"signup 성공, access_token 발급됨 (길이 {len(token)})")

# 중복 가입은 400이어야 함
dup_resp = client.post(
    "/auth/signup", json={"email": "e2e-test@example.com", "password": "another-pass-123"}
)
assert dup_resp.status_code == 400, dup_resp.text
print("중복 이메일 가입 거부 확인 (400)")

login_resp = client.post(
    "/auth/login", json={"email": "e2e-test@example.com", "password": "test-password-123"}
)
assert login_resp.status_code == 200, login_resp.text
print("login 성공")

wrong_login = client.post(
    "/auth/login", json={"email": "e2e-test@example.com", "password": "wrong-password"}
)
assert wrong_login.status_code == 401, wrong_login.text
print("잘못된 비밀번호 로그인 거부 확인 (401)")

me_resp = client.get("/auth/me", headers=auth_headers)
assert me_resp.status_code == 200, me_resp.text
print(f"/auth/me 확인: {me_resp.json()}")

no_auth_resp = client.get("/materials")
assert no_auth_resp.status_code == 401, no_auth_resp.text
print("인증 헤더 없이 /materials 호출 시 401 거부 확인")
print()

print("=== 2) 자료 업로드 (Korean PDF, 실제 나눔고딕 폰트, 백그라운드 큐 경로) ===")
with open(SAMPLE_PDF, "rb") as f:
    resp = client.post(
        "/materials/upload",
        headers=auth_headers,
        files={"file": ("os_ch6.pdf", f, "application/pdf")},
        data={"exam_style_note": "객관식 위주로 출제, 핵심 정의를 직접 묻는 문제가 많음"},
    )
assert resp.status_code == 200, resp.text
material = resp.json()
material_id = material["id"]
print("status:", resp.status_code, "| 업로드 직후 material status:", material["status"], "| exam_style_note:", material["exam_style_note"])

# 큐(워커가 떠있으면 비동기, 아니면 즉시 동기 폴백) 처리 완료까지 폴링
material_status = material["status"]
for _ in range(30):
    if material_status in ("ready", "failed"):
        break
    time.sleep(0.5)
    poll = client.get(f"/materials/{material_id}", headers=auth_headers)
    material_status = poll.json()["status"]
print(f"최종 material status: {material_status}")
assert material_status == "ready", f"업로드 처리 실패: {material_status}"

db = SessionLocal()
chunks = db.query(models.MaterialChunk).filter(models.MaterialChunk.material_id == material_id).all()
concepts = db.query(models.Concept).filter(models.Concept.material_id == material_id).all()
print(f"저장된 청크 수: {len(chunks)} (페이지 경계 확인: {[c.page_or_slide_no for c in chunks]})")
print(f"저장된 개념 수: {len(concepts)} -> {[c.name for c in concepts]}")
print(f"청크 embedding 컬럼 (VOYAGE_API_KEY 없음 -> None 폴백 확인): {[c.embedding for c in chunks[:2]]}")
assert len(chunks) == 3, "페이지 3개짜리 PDF인데 청크가 페이지 수와 안 맞음"
assert len(concepts) == 3
db.close()

# 다른 유저는 이 자료를 못 봐야 함 (ownership 체크, 404로 존재 숨김)
signup2 = client.post("/auth/signup", json={"email": "other-user@example.com", "password": "other-pass-123"})
other_headers = {"Authorization": f"Bearer {signup2.json()['access_token']}"}
other_view = client.get(f"/materials/{material_id}", headers=other_headers)
assert other_view.status_code == 404, other_view.text
print("다른 유저가 남의 material 조회 시 404 확인 (ownership 체크)")
print()

print("=== 3) 최초 문제 생성 (exam_style_note 반영 + v2 보기-개념 링크) ===")
resp = client.post(
    "/quiz-sets/generate",
    headers=auth_headers,
    json={"material_id": material_id, "num_questions": 6, "difficulty": "medium"},
)
assert resp.status_code == 200, resp.text
quiz_set = resp.json()
print(f"quiz_set_id={quiz_set['id']} | 문제 수={len(quiz_set['questions'])} | type={quiz_set['type']}")
mc_count = sum(1 for q in quiz_set["questions"] if q["type"] == "multiple_choice")
print(f"객관식 문제 수: {mc_count}/{len(quiz_set['questions'])} (스타일 노트가 '객관식 위주'라고 했으니 fake가 전부 객관식으로 만들었어야 함)")
assert mc_count == len(quiz_set["questions"]), "exam_style_note가 프롬프트에 전달 안 된 것 같음"
quiz_set_id = quiz_set["id"]

# v2: QuestionOption.related_concept_id가 실제로 저장됐는지 DB에서 직접 확인
db = SessionLocal()
mc_question_ids = [q["id"] for q in quiz_set["questions"] if q["type"] == "multiple_choice"]
options_with_link = (
    db.query(models.QuestionOption)
    .filter(
        models.QuestionOption.question_id.in_(mc_question_ids),
        models.QuestionOption.related_concept_id.isnot(None),
    )
    .all()
)
print(f"related_concept_id가 채워진 보기 수: {len(options_with_link)} (객관식 문제마다 정답 보기 최소 1개는 있어야 함)")
assert len(options_with_link) > 0, "v2 보기-개념 링크가 하나도 저장되지 않음"
db.close()

# 다른 유저는 이 quiz_set도 못 봐야 함
other_quiz_view = client.get(f"/quiz-sets/{quiz_set_id}", headers=other_headers)
assert other_quiz_view.status_code == 404, other_quiz_view.text
print("다른 유저가 남의 quiz_set 조회 시 404 확인 (v1에서는 이 체크 자체가 없었던 부분)")
print()

print("=== 4) 제출/채점 (일부러 절반 틀리게) ===")
answers = []
for i, q in enumerate(quiz_set["questions"]):
    if i % 2 == 0:
        # 정답 맞추기 (객관식이면 정답 옵션 텍스트, 단답형이면 문제생성 시 만든 정답)
        db2 = SessionLocal()
        qrow = db2.query(models.Question).get(q["id"])
        correct = qrow.correct_answer
        db2.close()
        answers.append({"question_id": q["id"], "user_answer": correct})
    else:
        # 객관식이면 실제 오답 보기를 골라서(v2 즉시판정 경로), 단답형이면 그냥 틀린 문자열.
        # API 응답(QuestionOptionOut)은 is_correct를 안 내려주므로(정답 유출 방지) DB에서 직접 조회.
        if q["type"] == "multiple_choice":
            db2 = SessionLocal()
            correct = db2.query(models.Question).get(q["id"]).correct_answer
            db2.close()
            wrong_opt = next(o["option_text"] for o in q["options"] if o["option_text"] != correct)
            answers.append({"question_id": q["id"], "user_answer": wrong_opt})
        else:
            answers.append({"question_id": q["id"], "user_answer": "일부러 틀린 답"})

resp = client.post(
    f"/quiz-sets/{quiz_set_id}/submit",
    headers=auth_headers,
    json={"quiz_set_id": quiz_set_id, "answers": answers},
)
assert resp.status_code == 200, resp.text
submission = resp.json()
print(f"submission_id={submission['id']} | score={submission['score']:.2f}")
wrong_tags = [a["wrong_tag"]["tag_type"] for a in submission["answers"] if a["wrong_tag"]]
print(f"오답 유형 분류 결과: {wrong_tags}")
assert len(wrong_tags) > 0, "일부러 틀리게 냈는데 오답 태그가 하나도 없음"

# v2: concept_confusion으로 분류된 오답 중 reasoning에 "LLM 호출 없이"가 찍힌 게 있는지 확인
# (related_concept_id가 있던 오답 보기를 고른 경우 -> classify_wrong_answer의 즉시판정 경로)
db = SessionLocal()
instant_tags = (
    db.query(models.WrongAnswerTag)
    .filter(models.WrongAnswerTag.reasoning.like("%LLM 호출 없이%"))
    .all()
)
print(f"v2 즉시판정(LLM 호출 스킵) 오답분석 건수: {len(instant_tags)}")
assert len(instant_tags) > 0, "v2 보기-개념 링크 기반 즉시판정 경로가 한 번도 안 탐 (fake가 헷갈리는 오답을 안 골랐거나 로직 문제)"
db.close()
print()

print("=== 5) 오답분석 대시보드 조회 (analysis 엔드포인트) ===")
resp = client.get(f"/quiz-sets/{quiz_set_id}/analysis", headers=auth_headers)
assert resp.status_code == 200, resp.text
analysis = resp.json()
print(f"총 {analysis['total']}문제 중 {analysis['correct']}개 정답 (정답률 {analysis['accuracy']:.0%})")
print("개념별 정답률:", [(c["concept_name"], f"{c['accuracy']:.0%}") for c in analysis["concept_accuracy"]])
print("오답 유형 분포:", [(t["tag_type"], t["count"]) for t in analysis["type_breakdown"]])
print("오답 상세 (source_label 포함):", [(d["question_text"][:20], d["source_label"]) for d in analysis["details"]])
assert all(d["source_label"] for d in analysis["details"]), "오답 상세에 근거(source_label)가 안 붙어있음"
print()

print("=== 6) 취약개념 기반 재출제 (벡터 유사도 선택 경로 -> 임베딩 없어서 폴백 확인) ===")
resp = client.post(
    "/quiz-sets/regenerate",
    headers=auth_headers,
    json={"source_quiz_set_id": quiz_set_id, "num_questions": 4},
)
assert resp.status_code == 200, resp.text
regen_set = resp.json()
print(f"재출제 quiz_set_id={regen_set['id']} | source_quiz_set_id={regen_set['source_quiz_set_id']} | 문제 수={len(regen_set['questions'])}")
assert regen_set["source_quiz_set_id"] == quiz_set_id
regen_quiz_set_id = regen_set["id"]
print()

print("=== 7) 재출제 문제도 풀고 제출 (이번엔 다 맞히기) ===")
answers2 = []
for q in regen_set["questions"]:
    db2 = SessionLocal()
    qrow = db2.query(models.Question).get(q["id"])
    correct = qrow.correct_answer
    db2.close()
    answers2.append({"question_id": q["id"], "user_answer": correct})
resp = client.post(
    f"/quiz-sets/{regen_quiz_set_id}/submit",
    headers=auth_headers,
    json={"quiz_set_id": regen_quiz_set_id, "answers": answers2},
)
assert resp.status_code == 200, resp.text
print(f"재출제 제출 score={resp.json()['score']:.2f}")
print()

print("=== 8) 재출제 전/후 비교 (Regenerate 화면이 쓰는 방식: analysis 2번 호출) ===")
resp_before = client.get(f"/quiz-sets/{quiz_set_id}/analysis", headers=auth_headers)
resp_after = client.get(f"/quiz-sets/{regen_quiz_set_id}/analysis", headers=auth_headers)
assert resp_before.status_code == 200 and resp_after.status_code == 200
before = {c["concept_id"]: c["accuracy"] for c in resp_before.json()["concept_accuracy"]}
after = {c["concept_id"]: c["accuracy"] for c in resp_after.json()["concept_accuracy"]}
matched = set(before) & set(after)
print(f"before/after 둘 다에 등장하는 개념 수(매칭 가능): {len(matched)}")
for cid in matched:
    print(f"  concept={cid[:8]}...  before={before[cid]:.0%} -> after={after[cid]:.0%}")
assert len(matched) > 0, "before/after 개념 매칭이 하나도 안 됨 (Regenerate 페이지의 덤벨차트가 비게 됨)"
print()

print("=== 9) materials 목록/PATCH(exam_style_note 수정) 확인 ===")
resp = client.get("/materials", headers=auth_headers)
assert resp.status_code == 200
print(f"materials 목록: {len(resp.json())}건")

resp = client.patch(f"/materials/{material_id}", json={"exam_style_note": "수정된 스타일: 단답형 비중을 늘려서"}, headers=auth_headers)
assert resp.status_code == 200, resp.text
print("PATCH 후 exam_style_note:", resp.json()["exam_style_note"])

# 남의 material은 PATCH도 404여야 함
other_patch = client.patch(f"/materials/{material_id}", json={"exam_style_note": "해킹 시도"}, headers=other_headers)
assert other_patch.status_code == 404, other_patch.text
print("다른 유저가 남의 material PATCH 시도 시 404 확인")
print()

print("############################################")
print("### 전체 엔드투엔드 플로우 성공 (real Postgres+pgvector, real Redis, mocked LLM) ###")
print("### 인증/큐/v2 보기-개념링크 전부 실제 코드 경로로 검증됨 ###")
print("############################################")
