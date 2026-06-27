"""Raw SQL operations for the users table."""
import sqlite3
from typing import Optional


def insert_user(conn: sqlite3.Connection, user_id: str, username: str,
                password_hash: str, created_at: str) -> None:
    conn.execute(
        "INSERT INTO users (user_id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (user_id, username, password_hash, created_at),
    )
    conn.commit()


def get_user_by_id(conn: sqlite3.Connection, user_id: str) -> Optional[sqlite3.Row]:
    cursor = conn.execute(
        "SELECT user_id, username, created_at FROM users WHERE user_id = ?",
        (user_id,),
    )
    return cursor.fetchone()


def get_user_by_username(conn: sqlite3.Connection, username: str) -> Optional[sqlite3.Row]:
    cursor = conn.execute(
        "SELECT user_id, username, password_hash, created_at FROM users WHERE username = ?",
        (username,),
    )
    return cursor.fetchone()
