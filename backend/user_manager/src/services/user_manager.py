"""Business logic for the users service (lightweight identity only)."""
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.db import db_operations
from src.db.connection import get_connection
from src.services import security


def _row_to_user(row: sqlite3.Row) -> dict:
    return {"user_id": row["user_id"], "username": row["username"]}


def create_user(username: str, password: str) -> Optional[dict]:
    """Register a new identity, storing only a salted hash of the password.

    Returns the new user, or None if the username is already taken (the caller
    maps that to a 400). The unique constraint is also caught directly, so two
    concurrent registrations of the same username cannot both succeed.
    """
    username = username.strip()
    conn = get_connection()
    try:
        if db_operations.get_user_by_username(conn, username) is not None:
            return None

        user_id = uuid.uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        password_hash = security.hash_password(password)
        try:
            db_operations.insert_user(conn, user_id, username, password_hash, created_at)
        except sqlite3.IntegrityError:
            return None
        return {"user_id": user_id, "username": username}
    finally:
        conn.close()


def authenticate(username: str, password: str) -> Optional[dict]:
    """Verify a username/password pair; return the identity or None on failure."""
    username = username.strip()
    conn = get_connection()
    try:
        row = db_operations.get_user_by_username(conn, username)
        if row is None:
            return None
        if not security.verify_password(password, row["password_hash"]):
            return None
        return _row_to_user(row)
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
