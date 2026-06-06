"""S2 最简规划最小回归：只守七段行程 schema、降级和 chat 的 plan 分支。

这些测试最初用于 TDD 的 RED 阶段；S2 实现后，它们作为最小回归保留。

测试边界：
- 不测真实 LLM 规划质量。
- 不测城市/日期槽位抽取，缺失追问留给 S3。
- 不测前端渲染，S2 仍只输出普通 text SSE。
"""

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.alpha._core import llm  # noqa: E402


def _load_itinerary():
    """加载 S2 新模块。

    如果这里失败，通常说明 S2 行程模块缺失；若失败信息不是缺模块，
    而是 Python path/IDEA 配置错误，才需要排查环境。
    """
    try:
        return importlib.import_module("agents.alpha._core.itinerary")
    except ModuleNotFoundError as exc:
        pytest.fail(f"S2 should provide agents.alpha._core.itinerary: {exc}")


def _events(lines: list[str]) -> list[dict]:
    parsed = []
    for line in lines:
        assert line.startswith("data: ")
        parsed.append(json.loads(line.removeprefix("data: ").strip()))
    return parsed


def _complete_itinerary() -> dict:
    return {
        "overview": "杭州一日游，节奏适中。",
        "timeline": "上午西湖，中午用餐，下午灵隐寺，傍晚返程。",
        "dining": "午餐可选杭帮菜。",
        "route": "西湖 -> 午餐 -> 灵隐寺 -> 返程。",
        "budget": "人均约 300-500 元。",
        "tips": "穿舒适鞋，提前确认开放时间。",
        "disclaimer": "信息仅供参考，出行前请确认实时信息。",
    }


def test_itinerary_generate_renders_required_sections(monkeypatch):
    """七段结构化结果齐全时，应渲染成可直接展示的一日游文本。"""
    itinerary = _load_itinerary()
    monkeypatch.setattr(llm, "generate_structured", lambda *args, **kwargs: _complete_itinerary())

    text = itinerary.generate([{"role": "user", "content": "周六去杭州玩一天"}])

    assert "## 一日游方案" in text
    for heading in ["概览", "时间轴", "餐饮", "路线", "预算", "贴士", "声明"]:
        assert f"### {heading}" in text
    assert "信息仅供参考" in text


def test_itinerary_generate_falls_back_when_structured_result_missing(monkeypatch):
    """结构化规划失败时，应返回朴素兜底文本，而不是让 plan 分支无输出。"""
    itinerary = _load_itinerary()
    monkeypatch.setattr(llm, "generate_structured", lambda *args, **kwargs: None)

    text = itinerary.generate([{"role": "user", "content": "周六去杭州玩一天"}])

    assert "简版一日游安排" in text
    assert "信息仅供参考" in text


def test_chat_plan_branch_uses_itinerary_without_qa_stream(monkeypatch):
    """chat() 遇到 plan 应调用 itinerary.generate，不应再走普通 qa stream。"""
    alpha = importlib.import_module("agents.alpha")
    monkeypatch.setattr(alpha, "intent", SimpleNamespace(route=lambda _messages: "plan"))
    monkeypatch.setattr(alpha, "itinerary", SimpleNamespace(generate=lambda _messages: "行程文本"), raising=False)

    def unexpected_stream_text(*_args, **_kwargs):
        raise AssertionError("plan branch should not use qa llm.stream_text")

    monkeypatch.setattr(alpha, "llm", SimpleNamespace(stream_text=unexpected_stream_text))

    events = _events(list(alpha.chat([{"role": "user", "content": "周六去杭州玩一天"}])))

    assert events == [{"type": "text", "delta": "行程文本"}, {"type": "done"}]
