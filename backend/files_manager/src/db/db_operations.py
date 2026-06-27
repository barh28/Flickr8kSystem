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


def all_caption_rows(conn: sqlite3.Connection) -> list:
    """Every row's id + captions, for recomputing derived fields in place."""
    return conn.execute(
        "SELECT id, caption_0, caption_1, caption_2, caption_3, caption_4 FROM files"
    ).fetchall()


def update_derived(conn: sqlite3.Connection, file_id: str,
                   caption_length: int, agreement: float) -> None:
    conn.execute(
        "UPDATE files SET caption_length = ?, agreement = ? WHERE id = ?",
        (caption_length, agreement, file_id),
    )


def _build_where(filters: dict) -> tuple:
    clauses = []
    params = []

    query_text = filters.get("q")
    if query_text:
        match_expr = _fts_query(query_text)
        if match_expr:
            fts_clause = "id IN (SELECT file_id FROM files_fts WHERE files_fts MATCH ?)"
            # or_ids lets a caller widen the text match to an extra id set (e.g. the
            # user's own labels matching the same text), so search = captions OR labels.
            or_ids = filters.get("or_ids")
            if or_ids:
                placeholders = ",".join("?" for _ in or_ids)
                clauses.append(f"({fts_clause} OR id IN ({placeholders}))")
                params.append(match_expr)
                params.extend(or_ids)
            else:
                clauses.append(fts_clause)
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

    # Numeric agreement threshold (0..1); keeps samples with at least this score.
    min_agreement = filters.get("min_agreement")
    if min_agreement is not None:
        clauses.append("agreement >= ?")
        params.append(min_agreement)

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


def get_stats(conn: sqlite3.Connection, dataset: Optional[str] = None) -> dict:
    """Dataset-wide distributions for the statistics dashboard.

    All distributions use a uniform {label, count} shape so the frontend can
    render them with one bar-chart component.
    """
    where = ""
    base_params: list = []
    if dataset:
        where = "WHERE dataset = ?"
        base_params = [dataset]

    total = conn.execute(f"SELECT COUNT(*) AS c FROM files {where}", base_params).fetchone()["c"]

    splits = conn.execute(
        f"SELECT split AS label, COUNT(*) AS count FROM files {where} GROUP BY split ORDER BY split",
        base_params,
    ).fetchall()
    orientations = conn.execute(
        f"SELECT orientation AS label, COUNT(*) AS count FROM files {where} "
        "GROUP BY orientation ORDER BY orientation",
        base_params,
    ).fetchall()

    length_agg = conn.execute(
        f"SELECT MIN(caption_length) AS mn, MAX(caption_length) AS mx, AVG(caption_length) AS av "
        f"FROM files {where}",
        base_params,
    ).fetchone()
    length_buckets = conn.execute(
        f"""
        SELECT
            SUM(CASE WHEN caption_length <= ? THEN 1 ELSE 0 END) AS short,
            SUM(CASE WHEN caption_length > ? AND caption_length <= ? THEN 1 ELSE 0 END) AS medium,
            SUM(CASE WHEN caption_length > ? THEN 1 ELSE 0 END) AS long
        FROM files {where}
        """,
        [SHORT_MAX_WORDS, SHORT_MAX_WORDS, MEDIUM_MAX_WORDS, MEDIUM_MAX_WORDS] + base_params,
    ).fetchone()

    agreement_agg = conn.execute(
        f"SELECT AVG(agreement) AS av FROM files {where}", base_params
    ).fetchone()
    agreement_buckets = conn.execute(
        f"""
        SELECT
            SUM(CASE WHEN agreement < 0.2 THEN 1 ELSE 0 END) AS b0,
            SUM(CASE WHEN agreement >= 0.2 AND agreement < 0.4 THEN 1 ELSE 0 END) AS b1,
            SUM(CASE WHEN agreement >= 0.4 AND agreement < 0.6 THEN 1 ELSE 0 END) AS b2,
            SUM(CASE WHEN agreement >= 0.6 AND agreement < 0.8 THEN 1 ELSE 0 END) AS b3,
            SUM(CASE WHEN agreement >= 0.8 THEN 1 ELSE 0 END) AS b4
        FROM files {where}
        """,
        base_params,
    ).fetchone()

    return {
        "total": total,
        "by_split": [{"label": r["label"], "count": r["count"]} for r in splits],
        "by_orientation": [{"label": r["label"], "count": r["count"]} for r in orientations],
        "caption_length": {
            "min": length_agg["mn"] or 0,
            "max": length_agg["mx"] or 0,
            "avg": round(length_agg["av"] or 0, 2),
            "buckets": [
                {"label": "short", "count": length_buckets["short"] or 0},
                {"label": "medium", "count": length_buckets["medium"] or 0},
                {"label": "long", "count": length_buckets["long"] or 0},
            ],
        },
        "agreement": {
            "avg": round(agreement_agg["av"] or 0, 3),
            "buckets": [
                {"label": "0–20%", "count": agreement_buckets["b0"] or 0},
                {"label": "20–40%", "count": agreement_buckets["b1"] or 0},
                {"label": "40–60%", "count": agreement_buckets["b2"] or 0},
                {"label": "60–80%", "count": agreement_buckets["b3"] or 0},
                {"label": "80–100%", "count": agreement_buckets["b4"] or 0},
            ],
        },
    }


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
