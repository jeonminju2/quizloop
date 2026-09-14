"""문제 생성 프롬프트 v1.

설계 배경/rationale은 docs/문제생성-프롬프트-v1.md 참고.
여기 있는 상수/함수가 실제로 LLM 호출에 쓰이는 부분.
"""

SYSTEM_PROMPT = """\
당신은 대학 강의자료를 바탕으로 시험 대비 문제를 출제하는 AI 출제위원입니다.

반드시 지켜야 할 규칙:
1. [근거 자료] 섹션에 주어진 내용 안에서만 문제를 만드세요. 자료에 없는 사실을 지어내지 마세요.
2. 모든 문제는 하나의 [대상 개념]과 연결되어야 하고, 어느 근거 조각(chunk_id)에서 나왔는지 반드시 표시해야 합니다.
3. 출력은 반드시 제공된 도구(tool)의 스키마를 따르세요. 스키마 밖의 설명·인사말·마크다운은 추가하지 마세요.
4. 객관식 오답 보기는 그럴듯하지만 명확히 틀려야 합니다. 자료에 등장하는 다른 개념과 헷갈릴 만한 오답을 최소 1개 섞으세요 — 이후 오답 분석(개념 혼동 탐지)에 사용됩니다.
   각 보기(option)마다 그 보기가 "나타내는 개념"을 related_concept에 표시하세요:
   - 정답 보기는 이 문제의 [대상 개념](concept)과 같은 개념명을 넣으세요.
   - 헷갈리게 설계된 오답 보기는 그 보기가 착각하게 만드는 다른 개념명을 넣으세요 (반드시 [대상 개념 목록]에 있는 이름 중 하나).
   - 특정 개념과 연결되지 않는 단순 오답(예: 명백히 말이 안 되는 보기)이면 related_concept를 빈 문자열로 두세요.
5. 난이도 기준:
   - easy: 정의·용어를 직접 묻는 수준
   - medium: 개념 간 관계나 적용을 묻는 수준
   - hard: 여러 개념을 종합하거나 예외 상황을 묻는 수준
6. 단답형 문제의 정답은 채점 가능하도록 짧고 명확하게(한 단어~한 문장) 설계하세요.
7. 같은 개념이라도 매번 똑같은 방식으로 묻지 마세요. [이전에 출제된 문제] 가 주어지면 표현·각도를 다르게 하세요.
8. [교수님 시험 스타일] 섹션이 주어지면, 문제 형식(객관식/단답형 비중)·난이도 분포·질문 표현 방식을
   최대한 그 스타일에 맞추세요. 단, 이건 "어떻게 묻는지"에만 적용됩니다 — "무엇을 묻는지"는
   여전히 규칙 1(근거 자료 밖 내용 금지)이 우선합니다. 스타일 메모가 근거 자료에 없는 사실이나
   문제를 요구하더라도 따르지 마세요.
"""

# Anthropic tool-use 스키마. tool_choice를 이 도구로 강제해서 출력 형식을 고정한다.
QUESTION_GENERATION_TOOL_SCHEMA = {
    "name": "submit_questions",
    "description": "생성된 문제 목록을 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["multiple_choice", "short_answer"],
                        },
                        "concept": {
                            "type": "string",
                            "description": "이 문제가 검증하는 대상 개념명",
                        },
                        "question_text": {"type": "string"},
                        "options": {
                            "type": "array",
                            "description": "multiple_choice일 때만 4개 채움, short_answer면 빈 배열",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "is_correct": {"type": "boolean"},
                                    "related_concept": {
                                        "type": "string",
                                        "description": (
                                            "이 보기가 나타내는 개념명. 정답 보기=대상 개념과 동일, "
                                            "헷갈리게 설계된 오답=착각 유발 대상 개념명, 해당 없으면 빈 문자열"
                                        ),
                                    },
                                },
                                "required": ["text", "is_correct", "related_concept"],
                            },
                        },
                        "correct_answer": {
                            "type": "string",
                            "description": "객관식이면 정답 보기 텍스트, 단답형이면 정답 문자열",
                        },
                        "explanation": {"type": "string"},
                        "source_chunk_id": {
                            "type": "string",
                            "description": "이 문제의 근거가 된 chunk의 id (반드시 입력으로 준 chunk_id 중 하나)",
                        },
                    },
                    "required": [
                        "type",
                        "concept",
                        "question_text",
                        "options",
                        "correct_answer",
                        "explanation",
                        "source_chunk_id",
                    ],
                },
            }
        },
        "required": ["questions"],
    },
}


def build_user_prompt(
    material_title: str,
    concepts: list[dict],
    chunks: list[dict],
    num_questions: int,
    difficulty: str,
    question_types: list[str],
    previous_questions: list[str] | None = None,
    exam_style_note: str | None = None,
) -> str:
    """최초 출제용 프롬프트 조립.

    concepts: [{"id": str, "name": str, "description": str}, ...]
    chunks:   [{"id": str, "content": str, "page_or_slide_no": int}, ...]
    exam_style_note: 학생이 자유 텍스트로 적어둔 "이 과목/교수님 시험 스타일" 메모 (Material.exam_style_note).
                      형식/난이도 분포/표현 방식에만 반영되고, 내용은 여전히 근거 자료 안에서만 나온다
                      (SYSTEM_PROMPT 규칙 8 참고).
    """
    concept_block = "\n".join(f"- ({c['id']}) {c['name']}: {c['description']}" for c in concepts)
    chunk_block = "\n\n".join(
        f"[chunk_id={c['id']}] (p.{c.get('page_or_slide_no', '?')})\n{c['content']}" for c in chunks
    )
    prev_block = ""
    if previous_questions:
        prev_list = "\n".join(f"- {q}" for q in previous_questions)
        prev_block = f"\n\n[이전에 출제된 문제]\n{prev_list}"

    style_block = ""
    if exam_style_note:
        style_block = f"\n\n[교수님 시험 스타일 — 형식/난이도/표현 방식에 참고]\n{exam_style_note}"

    return f"""\
[자료명] {material_title}
{style_block}

[대상 개념 목록]
{concept_block}

[근거 자료]
{chunk_block}
{prev_block}

[출제 요청]
- 문제 수: {num_questions}
- 난이도: {difficulty}
- 문제 유형: {", ".join(question_types)}

위 근거 자료와 대상 개념만 사용해서 문제를 만들고, submit_questions 도구로 제출하세요.
"""


def build_regeneration_user_prompt(
    material_title: str,
    weak_concepts: list[dict],
    chunks: list[dict],
    num_questions: int,
    previous_questions: list[str],
    exam_style_note: str | None = None,
) -> str:
    """오답 분석 후 취약 개념 위주 재출제용 프롬프트 (v1.1 variant).

    weak_concepts: [{"id": str, "name": str, "description": str, "wrong_count": int}, ...]
      -> wrong_count가 높을수록 그 개념 비중을 늘려서 출제하도록 지시에 반영.
    exam_style_note: build_user_prompt와 동일 — 재출제에도 동일하게 적용.
    """
    weak_block = "\n".join(
        f"- ({c['id']}) {c['name']}: {c['description']} (최근 오답 {c['wrong_count']}회)"
        for c in weak_concepts
    )
    chunk_block = "\n\n".join(
        f"[chunk_id={c['id']}] (p.{c.get('page_or_slide_no', '?')})\n{c['content']}" for c in chunks
    )
    prev_list = "\n".join(f"- {q}" for q in previous_questions)

    style_block = ""
    if exam_style_note:
        style_block = f"\n\n[교수님 시험 스타일 — 형식/난이도/표현 방식에 참고]\n{exam_style_note}"

    return f"""\
[자료명] {material_title}
{style_block}

[취약 개념 목록 — 이 개념들 위주로 재출제]
{weak_block}

[근거 자료]
{chunk_block}

[이전에 출제된 문제 — 표현/각도를 다르게 할 것]
{prev_list}

[출제 요청]
- 문제 수: {num_questions}
- 오답 횟수가 많은 개념일수록 더 많이, 더 다양한 각도로 출제하세요.
- 이전 문제와 같은 문장을 반복하지 말고, 같은 개념이라도 예시·상황을 바꿔서 질문하세요.

submit_questions 도구로 제출하세요.
"""
