"""SQLite connection handling and idempotent schema creation."""
import os
import sqlite3

from src.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       TEXT PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_password_column(conn: sqlite3.Connection) -> None:
    """Add password_hash to pre-existing DBs (idempotent migration)."""
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
    if "password_hash" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")


def init_db() -> None:
    """Create tables if they do not exist (safe to run on every startup)."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        _ensure_password_column(conn)
        conn.commit()
    finally:
        conn.close()
