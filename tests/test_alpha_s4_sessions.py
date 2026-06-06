"""S4 多会话持久化最小回归：只守会话历史 API 和消息写入编排。"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import server


def _events(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        assert block.startswith("data: ")
        events.append(json.loads(block.removeprefix("data: ").strip()))
    return events


def test_alpha_conversation_history_endpoint_reads_persisted_messages(monkeypatch):
    """GET history 应按 conversation_id 读取已持久化消息。"""
    monkeypatch.setattr(
        server,
        "alpha_storage",
        SimpleNamespace(
            list_messages=lambda conversation_id: [
                {"role": "user", "content": f"{conversation_id}: 你好"},
                {"role": "assistant", "content": "Alpha ready."},
            ],
        ),
        raising=False,
    )

    client = TestClient(server.create_app())

    response = client.get("/agents/alpha/conversations/demo-session/messages")

    assert response.status_code == 200
    # 这个接口必须由后端 API 返回 JSON,不能落到前端 SPA fallback 的 HTML。
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "messages": [
            {"role": "user", "content": "demo-session: 你好"},
            {"role": "assistant", "content": "Alpha ready."},
        ]
    }


def test_alpha_conversation_history_endpoint_uses_default_storage(monkeypatch):
    """生产路径应默认接入 alpha storage，而不是停在未配置状态。"""
    assert server.alpha_storage is not None
    monkeypatch.setattr(
        server.alpha_storage,
        "list_messages",
        lambda conversation_id: [{"role": "user", "content": f"{conversation_id}: ok"}],
    )

    client = TestClient(server.create_app())

    response = client.get("/agents/alpha/conversations/default-storage/messages")

    assert response.status_code == 200
    assert response.json() == {
        "messages": [{"role": "user", "content": "default-storage: ok"}]
    }


def test_create_app_ensures_alpha_storage_schema_on_startup(monkeypatch):
    """应用启动时应准备 alpha_messages 表，避免首次请求撞到缺表。"""
    calls = []
    monkeypatch.setattr(
        server,
        "alpha_storage",
        SimpleNamespace(ensure_schema=lambda: calls.append("ensure_schema")),
    )

    with TestClient(server.create_app()):
        pass

    assert calls == ["ensure_schema"]


def test_alpha_conversations_endpoint_lists_recent_conversations(monkeypatch):
    """GET conversations 应返回最近会话列表，给 New 后切回旧会话用。"""
    monkeypatch.setattr(
        server,
        "alpha_storage",
        SimpleNamespace(
            ensure_schema=lambda: None,
            list_conversations=lambda: [
                {
                    "conversation_id": "conv-2",
                    "title": "上海一日游",
                    "updated_at": "2026-06-06T10:00:00+08:00",
                },
                {
                    "conversation_id": "conv-1",
                    "title": "周六去杭州",
                    "updated_at": "2026-06-06T09:00:00+08:00",
                },
            ],
        ),
    )

    client = TestClient(server.create_app())

    response = client.get("/agents/alpha/conversations")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "conversations": [
            {
                "conversation_id": "conv-2",
                "title": "上海一日游",
                "updated_at": "2026-06-06T10:00:00+08:00",
            },
            {
                "conversation_id": "conv-1",
                "title": "周六去杭州",
                "updated_at": "2026-06-06T09:00:00+08:00",
            },
        ]
    }


def test_alpha_conversation_chat_uses_history_and_persists_both_messages(monkeypatch):
    """POST conversation chat 应用 DB 历史调用 alpha，并写入 user/assistant。"""
    append_calls = []
    captured = {}

    def list_messages(conversation_id):
        captured["history_id"] = conversation_id
        return [{"role": "user", "content": "周六去杭州"}]

    def append_message(conversation_id, role, content):
        append_calls.append((conversation_id, role, content))

    def chat(messages):
        captured["agent_messages"] = messages
        yield 'data: {"type":"text","delta":"行程"}\n\n'
        yield 'data: {"type":"text","delta":"已调整"}\n\n'
        yield 'data: {"type":"done"}\n\n'

    monkeypatch.setattr(
        server,
        "alpha_storage",
        SimpleNamespace(list_messages=list_messages, append_message=append_message),
        raising=False,
    )
    monkeypatch.setattr(server, "alpha", SimpleNamespace(chat=chat))

    client = TestClient(server.create_app())

    response = client.post(
        "/agents/alpha/conversations/demo-session/chat",
        json={"message": "砍到3个景点"},
    )

    assert response.status_code == 200
    assert _events(response.text) == [
        {"type": "text", "delta": "行程"},
        {"type": "text", "delta": "已调整"},
        {"type": "done"},
    ]
    assert captured["history_id"] == "demo-session"
    assert captured["agent_messages"] == [
        {"role": "user", "content": "周六去杭州"},
        {"role": "user", "content": "砍到3个景点"},
    ]
    assert append_calls == [
        ("demo-session", "user", "砍到3个景点"),
        ("demo-session", "assistant", "行程已调整"),
    ]
