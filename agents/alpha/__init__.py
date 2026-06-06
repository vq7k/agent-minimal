"""alpha agent —— 能力边界与最简规划编排入口。"""

import json
from collections.abc import Iterator

from agents.alpha._core import intent, itinerary, llm

SYSTEM_PROMPT = "你是一个友好的中文助手,回答简洁。"
OUT_OF_SCOPE_REPLY = (
    "我现在只专注做一日游规划，暂时不处理这类请求。"
    "你可以告诉我想去的城市、日期、同行人和偏好，我来帮你安排一天的路线。"
)


def _text(delta: str) -> str:
    event = {"type": "text", "delta": delta}
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _done() -> str:
    return 'data: {"type":"done"}\n\n'


def chat(messages: list[dict]) -> Iterator[str]:
    kind = intent.route(messages)
    if kind == "out_of_scope":
        yield _text(OUT_OF_SCOPE_REPLY)
        yield _done()
        return

    if kind == "plan":
        yield _text(itinerary.generate(messages))
        yield _done()
        return

    for delta in llm.stream_text(messages, system=SYSTEM_PROMPT):
        yield _text(delta)
    yield _done()
