"""S1 能力边界最小回归：只守路由分支和 chat 编排，不联网。

这些测试最初用于 TDD 的 RED 阶段；S1 实现后，它们作为最小回归保留。

测试边界：
- 不测 prompt 文案质量。
- 不测真实 LLM 分类准确率。
- 只测“LLM 结构化结果 -> 软件分支”这条工程控制点。
"""

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.alpha._core import llm  # noqa: E402


def _load_intent():
    """加载 S1 新模块。

    如果这里失败，通常说明 S1 路由模块缺失；若失败信息不是缺模块，而是
    Python path/IDEA 配置错误，才需要排查环境。
    """
    try:
        return importlib.import_module("agents.alpha._core.intent")
    except ModuleNotFoundError as exc:
        pytest.fail(f"S1 should provide agents.alpha._core.intent: {exc}")


def _events(lines: list[str]) -> list[dict]:
    """把 chat() 输出的 SSE 行转成事件对象。

    这里按 `data: {...}\n\n` 契约解析，但不绑定 JSON 空格格式，避免测试过脆。
    """
    parsed = []
    for line in lines:
        assert line.startswith("data: ")
        parsed.append(json.loads(line.removeprefix("data: ").strip()))
    return parsed


@pytest.mark.parametrize("kind", ["plan", "qa", "out_of_scope"])
def test_route_returns_valid_kind_from_structured_llm(monkeypatch, kind):
    """路由模块应原样返回合法的三分类结果。

    设计要求：`intent.route()` 只允许 `plan` / `qa` / `out_of_scope` 三个分支。
    这里 mock `llm.generate_structured`，因为测试目标不是模型，而是分类结果如何进入代码分支。
    """
    intent = _load_intent()

    monkeypatch.setattr(llm, "generate_structured", lambda *args, **kwargs: {"kind": kind})

    assert intent.route([{"role": "user", "content": "你好"}]) == kind


def test_route_degrades_to_qa_when_structured_result_missing(monkeypatch):
    """结构化路由失败时应降级到 qa，而不是误拒用户。

    设计要求：当 LLM 返回坏 JSON、校验失败或连续失败时，`generate_structured`
    会返回 None。此时默认 `qa`，让系统回到原有聊天兜底，避免把正常出游需求
    错杀成 `out_of_scope`。
    """
    intent = _load_intent()

    monkeypatch.setattr(llm, "generate_structured", lambda *args, **kwargs: None)

    assert intent.route([{"role": "user", "content": "周六去杭州玩一天"}]) == "qa"


def test_chat_refuses_out_of_scope_without_calling_openai(monkeypatch):
    """chat() 遇到 out_of_scope 应直接固定拒答，不再请求 OpenAI。

    设计要求：边界拒答是稳定产品行为，不交给 LLM 临场生成。测试里把 OpenAI
    替换成会报错的函数，确保实现必须先路由、再分支。
    """
    alpha = importlib.import_module("agents.alpha")
    monkeypatch.setattr(
        alpha, "intent", SimpleNamespace(route=lambda _messages: "out_of_scope"), raising=False
    )

    def unexpected_openai(*_args, **_kwargs):
        raise AssertionError("chat should route before calling OpenAI directly")

    monkeypatch.setattr(alpha, "OpenAI", unexpected_openai, raising=False)

    events = _events(list(alpha.chat([{"role": "user", "content": "帮我写首诗"}])))

    assert events[0]["type"] == "text"
    assert "一日游规划" in events[0]["delta"]
    assert events[-1] == {"type": "done"}


def test_chat_streams_qa_through_llm_stream_text(monkeypatch):
    """chat() 遇到 qa 应复用 _core.llm.stream_text，而不是继续在入口里直连 SDK。

    设计要求：S1 之后 `agents/alpha/__init__.py` 只做编排；LLM 访问统一收敛到
    `_core.llm`。这能让后续 plan / qa / out_of_scope 都经过同一套入口。
    """
    alpha = importlib.import_module("agents.alpha")
    monkeypatch.setattr(alpha, "intent", SimpleNamespace(route=lambda _messages: "qa"), raising=False)
    monkeypatch.setattr(
        alpha,
        "llm",
        SimpleNamespace(stream_text=lambda _messages, system=None: iter(["你好"])),
        raising=False,
    )

    def unexpected_openai(*_args, **_kwargs):
        raise AssertionError("chat should use llm.stream_text instead of OpenAI directly")

    monkeypatch.setattr(alpha, "OpenAI", unexpected_openai, raising=False)

    events = _events(list(alpha.chat([{"role": "user", "content": "你好"}])))

    assert events == [{"type": "text", "delta": "你好"}, {"type": "done"}]
