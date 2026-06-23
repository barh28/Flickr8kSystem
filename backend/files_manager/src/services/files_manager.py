"""Business logic for the files service."""
from typing import List, Optional

from src.config import DEFAULT_DATASET, IMAGE_URL_PREFIX
from src.db import db_operations
from src.db.connection import get_connection
from src.services import derive


def _row_to_item(row) -> dict:
    captions = []
    for index in range(5):
        caption = row[f"caption_{index}"]
        if caption is not None and caption != "":
            captions.append(caption)
    return {
        "id": row["id"],
        "image_url": f"{IMAGE_URL_PREFIX}/{row['id']}",
        "dataset": row["dataset"],
        "split": row["split"],
        "width": row["width"],
        "height": row["height"],
        "orientation": row["orientation"],
        "captions": captions,
        "caption_length": row["caption_length"],
        "agreement": row["agreement"],
    }


def list_files(filters: dict, sort: str, page: int, page_size: int) -> dict:
    conn = get_connection()
    try:
        total = db_operations.count_files(conn, filters)
        rows = db_operations.list_files(conn, filters, sort, page, page_size)
        items = [_row_to_item(row) for row in rows]
        return {"total": total, "page": page, "page_size": page_size, "items": items}
    finally:
        conn.close()


def get_file(file_id: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = db_operations.get_file(conn, file_id)
        if row is None:
            return None
        return _row_to_item(row)
    finally:
        conn.close()


def get_options() -> dict:
    conn = get_connection()
    try:
        return db_operations.get_options(conn)
    finally:
        conn.close()


def add_file(file_id: str, split: str, width: int, height: int,
             captions: List[str], image_path: str,
             dataset: Optional[str] = None) -> None:
    """Insert one sample, computing its derived fields.

    Building block reused by the ingestion step. `dataset` defaults to the
    configured dataset (Flickr8k) but is parameterized for future datasets.
    """
    record = {
        "id": file_id,
        "dataset": dataset if dataset else DEFAULT_DATASET,
        "split": split,
        "width": width,
        "height": height,
        "orientation": derive.compute_orientation(width, height),
        "captions": captions,
        "caption_length": derive.compute_caption_length(captions),
        "agreement": derive.compute_agreement(captions),
        "image_path": image_path,
    }
    conn = get_connection()
    try:
        db_operations.insert_file(conn, record)
    finally:
        conn.close()
