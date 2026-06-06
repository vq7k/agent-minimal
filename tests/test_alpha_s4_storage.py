"""S4 storage 最小回归：只守消息写入和按会话读取。"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _Cursor:
    def __init__(self, calls, rows=None):
        self.calls = calls
        self.rows = rows or []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows


class _Connection:
    def __init__(self, calls, rows=None):
        self.calls = calls
        self.rows = rows or []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _Cursor(self.calls, self.rows)


def test_append_message_inserts_conversation_scoped_message(monkeypatch):
    """append_message 应把 conversation_id/role/content 一起写入 alpha_messages。"""
    storage = importlib.import_module("agents.alpha._core.storage")
    calls = []
    monkeypatch.setattr(storage, "_connect", lambda: _Connection(calls))

    storage.append_message("conv-1", "user", "你好")

    sql, params = calls[-1]
    assert "INSERT INTO alpha_messages" in sql
    assert params == ("conv-1", "user", "你好")


def test_list_messages_reads_one_conversation_in_insert_order(monkeypatch):
    """list_messages 只读指定 conversation_id，并按插入顺序返回 role/content。"""
    storage = importlib.import_module("agents.alpha._core.storage")
    calls = []
    rows = [("user", "周六去杭州"), ("assistant", "Alpha ready.")]
    monkeypatch.setattr(storage, "_connect", lambda: _Connection(calls, rows))

    messages = storage.list_messages("conv-1")

    sql, params = calls[-1]
    assert "WHERE conversation_id = %s" in sql
    assert "ORDER BY id ASC" in sql
    assert params == ("conv-1",)
    assert messages == [
        {"role": "user", "content": "周六去杭州"},
        {"role": "assistant", "content": "Alpha ready."},
    ]
