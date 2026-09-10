"""Anthropic API 래퍼. 구조화 출력(tool_choice 강제)으로 JSON 파싱 안정성을 확보한다."""

import json

from anthropic import Anthropic

from app.config import settings

_client: Anthropic | None = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def call_with_tool_schema(
    system_prompt: str,
    user_prompt: str,
    tool_schema: dict,
    max_tokens: int = 4096,
) -> dict:
    """tool_choice를 강제해서 tool_schema에 정의된 JSON 구조로만 응답받는다.

    실패(스키마 불일치, API 에러) 시 최대 1회 재시도하고, 그래도 실패하면 예외를 던진다.
    호출부(services/question_generation.py 등)에서 잡아서 사용자에게 적절히 안내할 것.
    """
    client = get_client()

    for attempt in range(2):
        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=max_tokens,
            system=system_prompt,
            tools=[tool_schema],
            tool_choice={"type": "tool", "name": tool_schema["name"]},
            messages=[{"role": "user", "content": user_prompt}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == tool_schema["name"]:
                return block.input

        # tool_use 블록이 안 온 경우 (드물지만 발생 가능) - 재시도
        if attempt == 0:
            continue

    raise RuntimeError("LLM이 예상된 tool_use 형식으로 응답하지 않음 (2회 시도 실패)")
