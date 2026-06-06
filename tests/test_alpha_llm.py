"""T1 映射③核单测：只测确定性骨架（解析/校验/重试/降级/异常分层），全 mock，不联网。"""

import sys
from pathlib import Path

import httpx
import pytest
from openai import APIError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.alpha._core import llm  # noqa: E402


def test_valid(monkeypatch):
    monkeypatch.setattr(llm, "_complete_json", lambda u: '{"city": "杭州"}')
    assert llm.generate_structured("x", "{}", lambda d: "city" in d) == {"city": "杭州"}


def test_retry_then_ok(monkeypatch):
    seq = iter(["不是JSON", '{"a": 1}'])
    monkeypatch.setattr(llm, "_complete_json", lambda u: next(seq))
    assert llm.generate_structured("x", "{}", lambda d: True) == {"a": 1}


def test_all_fail_returns_none(monkeypatch):
    monkeypatch.setattr(llm, "_complete_json", lambda u: "坏的")
    assert llm.generate_structured("x", "{}", lambda d: True) is None


def test_validate_false_returns_none(monkeypatch):
    monkeypatch.setattr(llm, "_complete_json", lambda u: '{"a": 1}')
    assert llm.generate_structured("x", "{}", lambda d: False) is None


def test_non_dict_is_rejected(monkeypatch):
    seq = iter(["[1, 2, 3]", '{"a": 1}'])
    monkeypatch.setattr(llm, "_complete_json", lambda u: next(seq))
    assert llm.generate_structured("x", "{}", lambda d: True) == {"a": 1}


def test_apierror_is_retried_then_degrades(monkeypatch):
    def boom(_user):
        raise APIError("down", request=httpx.Request("POST", "http://test"), body=None)

    monkeypatch.setattr(llm, "_complete_json", boom)
    assert llm.generate_structured("x", "{}", lambda d: True) is None


def test_unexpected_error_propagates(monkeypatch):
    def boom(_user):
        raise RuntimeError("未设置 DEEPSEEK_API_KEY")

    monkeypatch.setattr(llm, "_complete_json", boom)
    with pytest.raises(RuntimeError):
        llm.generate_structured("x", "{}", lambda d: True)


def test_stream_text_yields_and_injects_system(monkeypatch):
    captured = {}

    def fake_create(*, model, messages, temperature, stream):
        captured["messages"] = messages

        class _Delta:
            content = "你好"

        class _Choice:
            delta = _Delta()

        class _Chunk:
            choices = [_Choice()]

        return iter([_Chunk()])

    class _FakeClient:
        class chat:  # noqa: N801
            class completions:  # noqa: N801
                create = staticmethod(fake_create)

    monkeypatch.setattr(llm, "_client", lambda: _FakeClient())
    out = "".join(llm.stream_text([{"role": "user", "content": "hi"}], system="S"))
    assert out == "你好"
    assert captured["messages"][0] == {"role": "system", "content": "S"}
