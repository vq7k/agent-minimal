"""Safely test the shared PostgreSQL database connection.

This demo verifies:
- the app can connect with DATABASE_URL
- the role can read connection metadata
- the role can write to a temporary table

It does not create or modify any persistent business table.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlsplit, urlunsplit

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _mask_database_url(url: str) -> str:
    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url

    userinfo, hostinfo = parts.netloc.rsplit("@", 1)
    if ":" in userinfo:
        username, _password = userinfo.split(":", 1)
        userinfo = f"{username}:***"
    else:
        userinfo = "***"
    return urlunsplit((parts.scheme, f"{userinfo}@{hostinfo}", parts.path, "", ""))


def _usage() -> str:
    return """Missing DATABASE_URL.

Examples:

  # Local shared PostgreSQL on this machine
  DATABASE_URL='postgresql://agent_minimal:<password>@localhost:5450/agent_minimal' \\
    uv run --with 'psycopg[binary]>=3' python scripts/demo_online_db.py

  # Production PostgreSQL through SSH tunnel
  ssh -i "$SSH_KEY" -N -L 15432:127.0.0.1:5450 "$SSH_USER@$SSH_HOST"
  DATABASE_URL='postgresql://agent_minimal:<password>@localhost:15432/agent_minimal' \\
    uv run --with 'psycopg[binary]>=3' python scripts/demo_online_db.py
"""


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(_usage(), file=sys.stderr)
        return 2

    try:
        import psycopg
    except ImportError:
        print(
            "Missing psycopg. Run with: "
            "uv run --with 'psycopg[binary]>=3' python scripts/demo_online_db.py",
            file=sys.stderr,
        )
        return 2

    print(f"Connecting to: {_mask_database_url(database_url)}")

    try:
        with psycopg.connect(database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      current_database(),
                      current_user,
                      inet_server_addr()::text,
                      inet_server_port(),
                      version()
                    """
                )
                database, user, server_addr, server_port, version = cur.fetchone()

                cur.execute(
                    """
                    CREATE TEMP TABLE alpha_db_demo_ping (
                      id INTEGER PRIMARY KEY,
                      note TEXT NOT NULL,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    ) ON COMMIT DROP
                    """
                )
                cur.execute(
                    """
                    INSERT INTO alpha_db_demo_ping (id, note)
                    VALUES (1, 'agent-minimal database demo')
                    RETURNING id, note, created_at
                    """
                )
                row = cur.fetchone()
    except Exception as exc:
        print(f"Database demo failed: {exc}", file=sys.stderr)
        return 1

    print("Database demo passed.")
    print(f"database: {database}")
    print(f"user: {user}")
    print(f"server: {server_addr}:{server_port}")
    print(f"postgres: {version.splitlines()[0]}")
    print(f"temp_write: id={row[0]}, note={row[1]}, created_at={row[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
