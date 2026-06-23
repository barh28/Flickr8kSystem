"""SQLite connection handling and idempotent schema creation for files."""
import os
import sqlite3

from src.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id             TEXT PRIMARY KEY,
    dataset        TEXT NOT NULL,
    split          TEXT NOT NULL,
    width          INTEGER NOT NULL,
    height         INTEGER NOT NULL,
    orientation    TEXT NOT NULL,
    caption_0      TEXT,
    caption_1      TEXT,
    caption_2      TEXT,
    caption_3      TEXT,
    caption_4      TEXT,
    caption_length INTEGER NOT NULL,
    agreement      REAL NOT NULL,
    image_path     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_files_dataset     ON files(dataset);
CREATE INDEX IF NOT EXISTS idx_files_split       ON files(split);
CREATE INDEX IF NOT EXISTS idx_files_length      ON files(caption_length);
CREATE INDEX IF NOT EXISTS idx_files_agreement   ON files(agreement);
CREATE INDEX IF NOT EXISTS idx_files_orientation ON files(orientation);

CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(file_id UNINDEXED, captions);
"""


def get_connection() -> sqlite3.Connection:
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables/indexes/FTS if they do not exist (safe on every startup)."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
