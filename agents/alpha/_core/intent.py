"""S1 意图路由：把用户输入分到 plan / qa / out_of_scope。"""

import json
from typing import Literal

from agents.alpha._core import llm

Kind = Literal["plan", "qa", "out_of_scope"]

_VALID_KINDS = {"plan", "qa", "out_of_scope"}
_SCHEMA_HINT = '{"kind":"plan|qa|out_of_scope"}'


def _validate_route(data: dict) -> bool:
    return data.get("kind") in _VALID_KINDS


def route(messages: list[dict]) -> Kind:
    """返回 alpha 的三分类路由结果。

    路由失败时兜 `qa`，避免把正常用户输入误拒成 out_of_scope。
    """
    if not messages:
        return "qa"

    prompt = f"""你是 alpha agent 的意图路由器。
alpha 只做一日游/出游规划相关对话。

请根据完整 messages 判断最后一条用户消息属于哪类：
- plan：用户想规划一日游、出游路线、景点、餐饮、预算、时间安排，或补充/修改出游需求。
- qa：寒暄，或询问 alpha 能做什么、如何使用 alpha。
- out_of_scope：明显与出游规划无关的创作、代码、通用问答、工作任务等。

messages:
{json.dumps(messages, ensure_ascii=False)}
"""
    data = llm.generate_structured(prompt, _SCHEMA_HINT, _validate_route)
    if data is None:
        return "qa"
    return data["kind"]  # type: ignore[return-value]
