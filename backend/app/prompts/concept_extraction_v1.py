"""핵심 개념 추출 프롬프트 v1.

업로드된 자료(청크 목록)를 보고 시험에 나올 법한 핵심 개념 목록을 뽑아낸다.
문제 생성 프롬프트(question_generation_v1)가 이 개념 목록을 대상으로 문제를 만들기 때문에,
여기서 개념을 너무 잘게 쪼개거나(문제 생성이 산만해짐) 너무 크게 묶으면(취약개념 추적이 무의미해짐)
오답분석의 정밀도가 떨어진다. "시험 문제 단위로 물어볼 수 있는 크기"를 기준으로 삼는다.
"""

SYSTEM_PROMPT = """\
당신은 강의자료에서 시험에 나올 법한 핵심 개념을 추출하는 AI 조교입니다.

반드시 지켜야 할 규칙:
1. [자료] 섹션에 실제로 등장하는 내용만 개념으로 뽑으세요. 자료에 없는 개념을 만들어내지 마세요.
2. 개념의 크기는 "문제 하나로 물어볼 수 있는 단위"여야 합니다.
   - 너무 큼 (X): "운영체제" 전체
   - 적당함 (O): "세마포어와 뮤텍스의 차이", "교착상태 발생 조건", "LRU 페이지 교체"
   - 너무 작음 (X): 자료의 한 문장을 그대로 개념 이름으로 쓰기
3. 각 개념은 1~2문장의 설명을 달아서, 나중에 문제 생성 AI가 이 설명만 보고도 문제를 낼 수 있게 하세요.
4. 개념 사이에 상위/하위 관계가 뚜렷하면 parent를 표시하세요 (없으면 생략).
5. 중복되거나 사실상 같은 개념은 하나로 합치세요.
6. 자료 분량에 맞게 개념 수를 정하세요 (대략 페이지/슬라이드 2~4개당 개념 1개 수준이 기준이지만, 내용 밀도에 따라 조정 가능).
"""

CONCEPT_EXTRACTION_TOOL_SCHEMA = {
    "name": "submit_concepts",
    "description": "추출한 핵심 개념 목록을 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "concepts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "개념명 (간결하게)"},
                        "description": {
                            "type": "string",
                            "description": "1~2문장 설명. 문제 생성 AI가 이것만 보고 문제를 낼 수 있어야 함",
                        },
                        "parent": {
                            "type": "string",
                            "description": "상위 개념명 (있으면). 없으면 빈 문자열",
                        },
                    },
                    "required": ["name", "description"],
                },
            }
        },
        "required": ["concepts"],
    },
}


def build_user_prompt(material_title: str, chunks: list[dict]) -> str:
    """chunks: [{"id": str, "content": str, "page_or_slide_no": int}, ...]"""
    chunk_block = "\n\n".join(
        f"[p.{c.get('page_or_slide_no', '?')}]\n{c['content']}" for c in chunks
    )
    return f"""\
[자료명] {material_title}

[자료]
{chunk_block}

위 자료에서 핵심 개념을 추출해서 submit_concepts 도구로 제출하세요.
"""
