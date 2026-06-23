"""Raw SQL operations for the tags table.

A tag is one row per (user_id, file_id) with a status. All access uses bind
parameters.
"""
import sqlite3
from typing import List, Optional


def upsert_tag(conn: sqlite3.Connection, user_id: str, file_id: str, status: str, updated_at: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO tags (user_id, file_id, status, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, file_id, status, updated_at),
    )


def remove_tags(conn: sqlite3.Connection, user_id: str, file_ids: List[str]) -> int:
    if len(file_ids) == 0:
        return 0
    placeholders = ",".join("?" for _ in file_ids)
    cursor = conn.execute(
        f"DELETE FROM tags WHERE user_id = ? AND file_id IN ({placeholders})",
        [user_id] + list(file_ids),
    )
    conn.commit()
    return cursor.rowcount


def get_status_map(conn: sqlite3.Connection, user_id: str, file_ids: List[str]) -> dict:
    if len(file_ids) == 0:
        return {}
    placeholders = ",".join("?" for _ in file_ids)
    rows = conn.execute(
        f"SELECT file_id, status FROM tags WHERE user_id = ? AND file_id IN ({placeholders})",
        [user_id] + list(file_ids),
    ).fetchall()
    return {row["file_id"]: row["status"] for row in rows}


def get_file_ids(conn: sqlite3.Connection, user_id: str, status: Optional[str] = None) -> List[str]:
    if status:
        rows = conn.execute(
            "SELECT file_id FROM tags WHERE user_id = ? AND status = ? ORDER BY file_id",
            (user_id, status),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT file_id FROM tags WHERE user_id = ? ORDER BY file_id",
            (user_id,),
        ).fetchall()
    return [row["file_id"] for row in rows]


def get_tagged(conn: sqlite3.Connection, user_id: str, status: Optional[str] = None) -> list:
    if status:
        return conn.execute(
            "SELECT file_id, status, updated_at FROM tags WHERE user_id = ? AND status = ? ORDER BY file_id",
            (user_id, status),
        ).fetchall()
    return conn.execute(
        "SELECT file_id, status, updated_at FROM tags WHERE user_id = ? ORDER BY file_id",
        (user_id,),
    ).fetchall()
