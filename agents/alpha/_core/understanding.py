"""S3 需求理解：抽取 city/date 并判断缺失。"""

import json

from agents.alpha._core import llm

REQUIRED_FIELDS = ("city", "date")
_SCHEMA_HINT = '{"city": "string|null", "date": "string|null"}'


def _validate_slots(data: dict) -> bool:
    return all(
        key in data and (data[key] is None or isinstance(data[key], str))
        for key in REQUIRED_FIELDS
    )


def _prompt(messages: list[dict]) -> str:
    return f"""你是 alpha 的出游需求理解器。
请从完整 messages 中抽取一日游规划必要信息。

只需要抽取：
- city：目的地城市或地点
- date：出游日期、星期、相对日期或时间表达

如果没有提到，字段填 null。

messages:
{json.dumps(messages, ensure_ascii=False)}
"""


def extract(messages: list[dict]) -> dict:
    data = llm.generate_structured(_prompt(messages), _SCHEMA_HINT, _validate_slots)
    if data is None:
        return {"city": None, "date": None}
    return {key: data.get(key) for key in REQUIRED_FIELDS}


def missing(slots: dict) -> list[str]:
    return [key for key in REQUIRED_FIELDS if not slots.get(key)]


def ask(missing_fields: list[str]) -> str:
    fields = set(missing_fields)
    if fields == {"city"}:
        return "你想去哪个城市或地点玩？"
    if fields == {"date"}:
        return "你计划哪天出发？"
    return (
        "我需要先确认目的地和日期："
        "你想去哪个城市或地点，计划哪天出发？"
    )
