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


def get_status_counts(conn: sqlite3.Connection, user_id: str) -> dict:
    """{status: count} of this user's tags, for the statistics dashboard."""
    rows = conn.execute(
        "SELECT status, COUNT(*) AS count FROM tags WHERE user_id = ? GROUP BY status",
        (user_id,),
    ).fetchall()
    return {row["status"]: row["count"] for row in rows}


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


# --- Labels (free-form, per-user) -------------------------------------------

def add_label(conn: sqlite3.Connection, user_id: str, file_id: str, label: str, updated_at: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO labels (user_id, file_id, label, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, file_id, label, updated_at),
    )


def remove_label(conn: sqlite3.Connection, user_id: str, file_ids: List[str], label: str) -> int:
    if len(file_ids) == 0:
        return 0
    placeholders = ",".join("?" for _ in file_ids)
    cursor = conn.execute(
        f"DELETE FROM labels WHERE user_id = ? AND label = ? AND file_id IN ({placeholders})",
        [user_id, label] + list(file_ids),
    )
    conn.commit()
    return cursor.rowcount


def get_labels_map(conn: sqlite3.Connection, user_id: str, file_ids: List[str]) -> dict:
    """Return {file_id: [label, ...]} for the given files (this user only)."""
    if len(file_ids) == 0:
        return {}
    placeholders = ",".join("?" for _ in file_ids)
    rows = conn.execute(
        f"SELECT file_id, label FROM labels WHERE user_id = ? AND file_id IN ({placeholders}) "
        "ORDER BY label",
        [user_id] + list(file_ids),
    ).fetchall()
    result: dict = {}
    for row in rows:
        result.setdefault(row["file_id"], []).append(row["label"])
    return result


def get_file_ids_by_labels(conn: sqlite3.Connection, user_id: str, labels: List[str]) -> List[str]:
    """File ids carrying ANY of the given labels (exact match) for this user."""
    if len(labels) == 0:
        return []
    placeholders = ",".join("?" for _ in labels)
    rows = conn.execute(
        f"SELECT DISTINCT file_id FROM labels WHERE user_id = ? AND label IN ({placeholders})",
        [user_id] + list(labels),
    ).fetchall()
    return [row["file_id"] for row in rows]


def search_label_file_ids(conn: sqlite3.Connection, user_id: str, text: str) -> List[str]:
    """File ids whose label contains `text` (substring), for the search union."""
    needle = text.strip().lower()
    if not needle:
        return []
    rows = conn.execute(
        "SELECT DISTINCT file_id FROM labels WHERE user_id = ? AND label LIKE ? ESCAPE '\\'",
        (user_id, "%" + _escape_like(needle) + "%"),
    ).fetchall()
    return [row["file_id"] for row in rows]


def get_label_options(conn: sqlite3.Connection, user_id: str) -> list:
    """Distinct labels for this user with usage counts, for filter chips."""
    return conn.execute(
        "SELECT label, COUNT(*) AS count FROM labels WHERE user_id = ? "
        "GROUP BY label ORDER BY label",
        (user_id,),
    ).fetchall()


def _escape_like(text: str) -> str:
    """Escape LIKE wildcards so user text is matched literally."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
