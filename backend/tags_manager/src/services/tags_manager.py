"""Business logic for the tags service.

Owns user tags and orchestrates tag-aware gallery queries by calling the files
and users services directly. Dependency direction is strictly tags -> files/users.
"""
from datetime import datetime, timezone
from typing import List, Optional

from src.config import FILES_PAGE_LIMIT
from src.db import db_operations
from src.db.connection import get_connection
from src.services import clients


def _chunks(items: List[str], size: int) -> List[List[str]]:
    chunks = []
    start = 0
    while start < len(items):
        chunks.append(items[start:start + size])
        start += size
    return chunks


def _user_exists(user_id: str) -> bool:
    response = clients.users_client.get("get", params={"id": user_id})
    return response.status_code == 200


def _fetch_files_metadata(file_ids: List[str]) -> dict:
    """Return {id: file_item} for the given ids (chunked to respect page size)."""
    metadata = {}
    for chunk in _chunks(file_ids, FILES_PAGE_LIMIT):
        response = clients.files_client.get("list", params={"ids": chunk, "page_size": len(chunk)})
        if response.status_code == 200:
            for item in response.json()["items"]:
                metadata[item["id"]] = item
    return metadata


def _files_list(params: dict) -> dict:
    response = clients.files_client.get("list", params=params)
    if response.status_code != 200:
        raise RuntimeError("files service returned an error")
    return response.json()


def _files_params(file_filters: dict, sort: str, page: int, page_size: int) -> dict:
    params = {"page": page, "page_size": page_size, "sort": sort}
    for key, value in file_filters.items():
        if value:
            params[key] = value
    return params


def set_tags(user_id: str, file_ids: List[str], status: str) -> Optional[dict]:
    """Tag files for a user after validating the user and files exist.

    Returns None if the user does not exist; otherwise a summary. Files that do
    not exist are skipped (never written as invalid associations).
    """
    if not _user_exists(user_id):
        return None

    requested = list(dict.fromkeys(file_ids))
    existing = set(_fetch_files_metadata(requested).keys())
    valid = [file_id for file_id in requested if file_id in existing]
    missing = [file_id for file_id in requested if file_id not in existing]

    updated_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        for file_id in valid:
            db_operations.upsert_tag(conn, user_id, file_id, status, updated_at)
        conn.commit()
    finally:
        conn.close()

    return {"tagged": len(valid), "skipped_missing": missing}


def remove_tags(user_id: str, file_ids: List[str]) -> dict:
    conn = get_connection()
    try:
        removed = db_operations.remove_tags(conn, user_id, file_ids)
    finally:
        conn.close()
    return {"removed": removed}


def query(user_id: str, status: Optional[str], file_filters: dict,
          sort: str, page: int, page_size: int) -> dict:
    """Gallery orchestrator: filter (optionally by tag status) + annotate."""
    conn = get_connection()
    try:
        params = _files_params(file_filters, sort, page, page_size)

        if status:
            tagged_ids = db_operations.get_file_ids(conn, user_id, status)
            if len(tagged_ids) == 0:
                return {"total": 0, "page": page, "page_size": page_size, "items": []}
            params["ids"] = tagged_ids

        result = _files_list(params)

        page_ids = [item["id"] for item in result["items"]]
        status_map = db_operations.get_status_map(conn, user_id, page_ids)
        for item in result["items"]:
            item["tag_status"] = status_map.get(item["id"])
        return result
    finally:
        conn.close()


def export(user_id: str, status: Optional[str]) -> List[dict]:
    """Build the tagged subset (id + status + file metadata) for export."""
    conn = get_connection()
    try:
        tagged = db_operations.get_tagged(conn, user_id, status)
    finally:
        conn.close()

    file_ids = [row["file_id"] for row in tagged]
    status_by_id = {row["file_id"]: row["status"] for row in tagged}
    metadata = _fetch_files_metadata(file_ids)

    records = []
    for file_id in file_ids:
        item = metadata.get(file_id, {})
        records.append({
            "id": file_id,
            "status": status_by_id.get(file_id),
            "dataset": item.get("dataset"),
            "split": item.get("split"),
            "captions": item.get("captions", []),
        })
    return records
