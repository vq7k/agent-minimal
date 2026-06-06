"""S3 缺失追问最小回归：只守 city/date 缺失判定和 chat 编排。

这些测试先作为 TDD 的 RED 阶段存在；S3 实现后，它们作为最小回归保留。

测试边界：
- 不测真实 LLM 的理解质量，只 mock 结构化输出。
- 不测复杂多轮状态机，S3 只要求本轮能一次性追问缺失字段。
- 不测前端渲染，仍只检查后端 SSE 事件。
"""

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.alpha._core import llm  # noqa: E402


def _load_understanding():
    """加载 S3 新模块。

    如果这里失败，通常说明 S3 的需求理解模块还没实现；这就是 RED 阶段
    预期暴露的缺口。
    """
    try:
        return importlib.import_module("agents.alpha._core.understanding")
    except ModuleNotFoundError as exc:
        pytest.fail(f"S3 should provide agents.alpha._core.understanding: {exc}")


def _events(lines: list[str]) -> list[dict]:
    parsed = []
    for line in lines:
        assert line.startswith("data: ")
        parsed.append(json.loads(line.removeprefix("data: ").strip()))
    return parsed


def test_extract_slots_keeps_plan_ready_when_city_and_date_present(monkeypatch):
    """city/date 都抽到时，missing 应为空，chat 才能继续进入 S2 行程生成。"""
    understanding = _load_understanding()
    monkeypatch.setattr(
        llm,
        "generate_structured",
        lambda *args, **kwargs: {"city": "杭州", "date": "周六"},
    )

    slots = understanding.extract([{"role": "user", "content": "周六去杭州玩一天"}])

    assert slots == {"city": "杭州", "date": "周六"}
    assert understanding.missing(slots) == []


def test_missing_asks_city_when_city_missing():
    """缺 city 时只追问目的地，不额外打断日期等已知信息。"""
    understanding = _load_understanding()
    slots = {"city": None, "date": "周六"}

    missing = understanding.missing(slots)

    assert missing == ["city"]
    assert "城市或地点" in understanding.ask(missing)


def test_missing_asks_date_when_date_missing():
    """缺 date 时只追问出发日期，避免把已知目的地再次问一遍。"""
    understanding = _load_understanding()
    slots = {"city": "杭州", "date": None}

    missing = understanding.missing(slots)

    assert missing == ["date"]
    assert "哪天" in understanding.ask(missing)


def test_missing_asks_city_and_date_together_when_both_missing():
    """city/date 都缺时，应一次性问清，不要连续追问两轮。"""
    understanding = _load_understanding()
    slots = {"city": None, "date": None}

    missing = understanding.missing(slots)
    question = understanding.ask(missing)

    assert missing == ["city", "date"]
    assert "目的地" in question
    assert "日期" in question


def test_chat_plan_branch_asks_missing_info_without_generating_itinerary(monkeypatch):
    """plan 缺必要信息时，应返回追问 SSE，并且不能调用 itinerary.generate。"""
    alpha = importlib.import_module("agents.alpha")
    question = (
        "我需要先确认目的地和日期："
        "你想去哪个城市或地点，计划哪天出发？"
    )

    monkeypatch.setattr(alpha, "intent", SimpleNamespace(route=lambda _messages: "plan"))
    monkeypatch.setattr(
        alpha,
        "understanding",
        SimpleNamespace(
            extract=lambda _messages: {"city": None, "date": None},
            missing=lambda _slots: ["city", "date"],
            ask=lambda _missing: question,
        ),
        raising=False,
    )

    def unexpected_generate(*_args, **_kwargs):
        raise AssertionError("missing city/date should ask user before itinerary.generate")

    monkeypatch.setattr(
        alpha,
        "itinerary",
        SimpleNamespace(generate=unexpected_generate),
        raising=False,
    )

    events = _events(list(alpha.chat([{"role": "user", "content": "我想出去玩"}])))

    assert events == [{"type": "text", "delta": question}, {"type": "done"}]


def test_chat_plan_branch_checks_slots_before_generating_itinerary(monkeypatch):
    """plan 信息齐全时也要先过槽位判定，再复用 S2 生成行程。"""
    alpha = importlib.import_module("agents.alpha")
    called = {"extract": False}

    def extract(_messages):
        called["extract"] = True
        return {"city": "杭州", "date": "周六"}

    monkeypatch.setattr(alpha, "intent", SimpleNamespace(route=lambda _messages: "plan"))
    monkeypatch.setattr(
        alpha,
        "understanding",
        SimpleNamespace(
            extract=extract,
            missing=lambda _slots: [],
            ask=lambda _missing: "不应追问",
        ),
        raising=False,
    )
    monkeypatch.setattr(
        alpha,
        "itinerary",
        SimpleNamespace(generate=lambda _messages: "行程文本"),
        raising=False,
    )

    events = _events(list(alpha.chat([{"role": "user", "content": "周六去杭州玩一天"}])))

    assert called["extract"] is True
    assert events == [{"type": "text", "delta": "行程文本"}, {"type": "done"}]
