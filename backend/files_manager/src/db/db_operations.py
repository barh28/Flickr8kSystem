"""Raw SQL operations for the files table (+ FTS index).

All dynamic filtering uses bind parameters; sort/length/agreement values are
mapped through whitelists, so user input never reaches the SQL text directly.
"""
import re
import sqlite3
from typing import Optional

from src.config import AGREEMENT_HIGH_THRESHOLD, MEDIUM_MAX_WORDS, SHORT_MAX_WORDS

# sort key -> (column, direction). `random` is handled separately.
_SORT_COLUMNS = {
    "id": ("id", "ASC"),
    "length": ("caption_length", "ASC"),
    "agreement": ("agreement", "DESC"),
}

_WS_RE = re.compile(r"\s+")


def _cap(captions: list, index: int) -> Optional[str]:
    if index < len(captions):
        return captions[index]
    return None


def _fts_query(raw: str) -> str:
    """Turn free text into a safe FTS5 MATCH expression (AND of quoted terms)."""
    tokens = [t for t in _WS_RE.split(raw.strip()) if t]
    quoted = ['"' + t.replace('"', '""') + '"' for t in tokens]
    return " ".join(quoted)


def insert_file(conn: sqlite3.Connection, record: dict) -> None:
    captions = record["captions"]
    conn.execute(
        """
        INSERT OR REPLACE INTO files
            (id, dataset, split, width, height, orientation,
             caption_0, caption_1, caption_2, caption_3, caption_4,
             caption_length, agreement, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["id"], record["dataset"], record["split"], record["width"],
            record["height"], record["orientation"],
            _cap(captions, 0), _cap(captions, 1), _cap(captions, 2),
            _cap(captions, 3), _cap(captions, 4),
            record["caption_length"], record["agreement"], record["image_path"],
        ),
    )
    conn.execute("DELETE FROM files_fts WHERE file_id = ?", (record["id"],))
    joined = " ".join(c for c in captions if c)
    conn.execute(
        "INSERT INTO files_fts (file_id, captions) VALUES (?, ?)",
        (record["id"], joined),
    )
    conn.commit()


def _build_where(filters: dict) -> tuple:
    clauses = []
    params = []

    query_text = filters.get("q")
    if query_text:
        match_expr = _fts_query(query_text)
        if match_expr:
            clauses.append("id IN (SELECT file_id FROM files_fts WHERE files_fts MATCH ?)")
            params.append(match_expr)

    ids = filters.get("ids")
    if ids:
        placeholders = ",".join("?" for _ in ids)
        clauses.append(f"id IN ({placeholders})")
        params.extend(ids)

    dataset = filters.get("dataset")
    if dataset:
        clauses.append("dataset = ?")
        params.append(dataset)

    split = filters.get("split")
    if split:
        clauses.append("split = ?")
        params.append(split)

    orientation = filters.get("orientation")
    if orientation:
        clauses.append("orientation = ?")
        params.append(orientation)

    length = filters.get("length")
    if length == "short":
        clauses.append("caption_length <= ?")
        params.append(SHORT_MAX_WORDS)
    elif length == "medium":
        clauses.append("caption_length > ? AND caption_length <= ?")
        params.extend([SHORT_MAX_WORDS, MEDIUM_MAX_WORDS])
    elif length == "long":
        clauses.append("caption_length > ?")
        params.append(MEDIUM_MAX_WORDS)

    agreement = filters.get("agreement")
    if agreement == "high":
        clauses.append("agreement >= ?")
        params.append(AGREEMENT_HIGH_THRESHOLD)
    elif agreement == "low":
        clauses.append("agreement < ?")
        params.append(AGREEMENT_HIGH_THRESHOLD)

    where = ""
    if clauses:
        where = "WHERE " + " AND ".join(clauses)
    return where, params


def count_files(conn: sqlite3.Connection, filters: dict) -> int:
    where, params = _build_where(filters)
    row = conn.execute(f"SELECT COUNT(*) AS c FROM files {where}", params).fetchone()
    return row["c"]


def list_files(conn: sqlite3.Connection, filters: dict, sort: str, page: int, page_size: int) -> list:
    where, params = _build_where(filters)
    if sort == "random":
        order = "ORDER BY RANDOM()"
    else:
        column, direction = _SORT_COLUMNS.get(sort, _SORT_COLUMNS["id"])
        order = f"ORDER BY {column} {direction}, id ASC"
    offset = (page - 1) * page_size
    sql = f"SELECT * FROM files {where} {order} LIMIT ? OFFSET ?"
    return conn.execute(sql, params + [page_size, offset]).fetchall()


def get_file(conn: sqlite3.Connection, file_id: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()


def get_options(conn: sqlite3.Connection) -> dict:
    datasets = [r["dataset"] for r in conn.execute("SELECT DISTINCT dataset FROM files ORDER BY dataset")]
    splits = [r["split"] for r in conn.execute("SELECT DISTINCT split FROM files ORDER BY split")]
    orientations = [r["orientation"] for r in conn.execute("SELECT DISTINCT orientation FROM files ORDER BY orientation")]
    bounds = conn.execute("SELECT MIN(caption_length) AS mn, MAX(caption_length) AS mx FROM files").fetchone()
    minimum = bounds["mn"] if bounds["mn"] is not None else 0
    maximum = bounds["mx"] if bounds["mx"] is not None else 0
    return {
        "datasets": datasets,
        "splits": splits,
        "orientations": orientations,
        "word_count": {"min": minimum, "max": maximum},
    }
