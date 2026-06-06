"""S4 alpha 会话消息存储。"""

import os

import psycopg


def _database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is required")
    return value


def _connect():
    return psycopg.connect(_database_url())


def ensure_schema() -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alpha_messages (
              id BIGSERIAL PRIMARY KEY,
              conversation_id TEXT NOT NULL,
              role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
              content TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alpha_messages_conversation_id_id
            ON alpha_messages (conversation_id, id)
            """
        )


def append_message(conversation_id: str, role: str, content: str) -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alpha_messages (conversation_id, role, content)
            VALUES (%s, %s, %s)
            """,
            (conversation_id, role, content),
        )


def list_messages(conversation_id: str) -> list[dict]:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT role, content
            FROM alpha_messages
            WHERE conversation_id = %s
            ORDER BY id ASC
            """,
            (conversation_id,),
        )
        return [{"role": role, "content": content} for role, content in cur.fetchall()]
