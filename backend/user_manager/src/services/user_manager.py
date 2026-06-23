"""Business logic for the users service (lightweight identity only)."""
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.db import db_operations
from src.db.connection import get_connection


def _row_to_user(row: sqlite3.Row) -> dict:
    return {"user_id": row["user_id"], "username": row["username"]}


def create_user(username: str) -> dict:
    """Get-or-create an identity by username.

    Acts as a lightweight login: typing an existing username returns the same
    identity instead of failing, so a returning user keeps their tags.
    """
    username = username.strip()
    conn = get_connection()
    try:
        existing = db_operations.get_user_by_username(conn, username)
        if existing is not None:
            return _row_to_user(existing)

        user_id = uuid.uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        db_operations.insert_user(conn, user_id, username, created_at)
        return {"user_id": user_id, "username": username}
    finally:
        conn.close()


def get_user(user_id: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = db_operations.get_user_by_id(conn, user_id)
        if row is None:
            return None
        return _row_to_user(row)
    finally:
        conn.close()
