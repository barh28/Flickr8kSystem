"""SQLite connection handling and idempotent schema creation for tags."""
import os
import sqlite3

from src.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS tags (
    user_id    TEXT NOT NULL,
    file_id    TEXT NOT NULL,
    status     TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, file_id)
);
CREATE INDEX IF NOT EXISTS idx_tags_user_status ON tags(user_id, status);
"""


def get_connection() -> sqlite3.Connection:
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
