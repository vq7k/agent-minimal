"""S2 最简行程生成：一次 LLM 产出整份一日游方案。"""

import json

from agents.alpha._core import llm

REQUIRED_SECTIONS = (
    "overview",
    "timeline",
    "dining",
    "route",
    "budget",
    "tips",
    "disclaimer",
)

_SCHEMA_HINT = """{
  "overview": "概览",
  "timeline": "一天时间轴",
  "dining": "餐饮建议",
  "route": "路线安排",
  "budget": "预算估算",
  "tips": "出行贴士",
  "disclaimer": "信息仅供参考声明"
}"""

_HEADINGS = {
    "overview": "概览",
    "timeline": "时间轴",
    "dining": "餐饮",
    "route": "路线",
    "budget": "预算",
    "tips": "贴士",
    "disclaimer": "声明",
}


def _validate_itinerary(data: dict) -> bool:
    return all(isinstance(data.get(key), str) and data[key].strip() for key in REQUIRED_SECTIONS)


def _prompt(messages: list[dict]) -> str:
    return f"""你是 alpha，一日游规划助手。
请根据完整 messages，为用户生成一份一日游方案。

要求：
- 只规划一天。
- 内容要具体、可读、适合直接展示给用户。
- 必须包含概览、时间轴、餐饮、路线、预算、贴士、声明。
- 声明必须表达“信息仅供参考，出行前请确认实时信息”。
- 当前不接真实天气/票务/餐厅 API，不要假装实时查询。

messages:
{json.dumps(messages, ensure_ascii=False)}
"""


def _fallback_text() -> str:
    return (
        "我可以先给你一个简版一日游安排：上午选择城市核心景点，"
        "中午在附近用餐，下午安排第二个景点或城市漫步，傍晚返程。"
        "信息仅供参考，出行前请确认天气、营业时间和交通情况。"
    )


def render(data: dict) -> str:
    parts = ["## 一日游方案"]
    for key in REQUIRED_SECTIONS:
        parts.append(f"### {_HEADINGS[key]}\n{data[key].strip()}")
    return "\n\n".join(parts)


def generate(messages: list[dict]) -> str:
    data = llm.generate_structured(_prompt(messages), _SCHEMA_HINT, _validate_itinerary)
    if data is None:
        return _fallback_text()
    return render(data)
