"""Business logic for the tags service.

Owns user tags and orchestrates tag-aware gallery queries by calling the files
and users services directly. Dependency direction is strictly tags -> files/users.
"""
from datetime import datetime, timezone
from typing import List, Optional

from src.config import CLIP_CANDIDATES, FILES_PAGE_LIMIT, PUBLIC_BASE_URL
from src.db import db_operations
from src.db.connection import get_connection
from src.services import clients


class SemanticUnavailable(Exception):
    """The CLIP service is reachable but its index is not ready yet."""


def _chunks(items: List[str], size: int) -> List[List[str]]:
    chunks = []
    start = 0
    while start < len(items):
        chunks.append(items[start:start + size])
        start += size
    return chunks


def _norm_label(label: str) -> str:
    """Normalize a label so "Dogs", " dogs " and "dogs" are the same tag."""
    return (label or "").strip().lower()


def _user_exists(user_id: str) -> bool:
    response = clients.users_client.get("get", params={"id": user_id})
    return response.status_code == 200


def _fetch_files_metadata(file_ids: List[str]) -> dict:
    """Return {id: file_item} for the given ids (chunked to respect page size)."""
    return _fetch_filtered_metadata(file_ids, {})


def _fetch_filtered_metadata(file_ids: List[str], facet_filters: dict) -> dict:
    """Like _fetch_files_metadata but only keeps ids that also pass the given
    facet filters (split / length / orientation / agreement / dataset). Used by
    meaning search to apply the user's filters on top of semantic ranking."""
    metadata = {}
    for chunk in _chunks(file_ids, FILES_PAGE_LIMIT):
        params = {"ids": chunk, "page_size": len(chunk)}
        params.update(facet_filters)
        response = clients.files_client.get("list", params=params)
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


def _restrict_ids(conn, user_id: str, status: Optional[str],
                  labels: Optional[List[str]]) -> Optional[set]:
    """The set of file ids the user's status/label filters allow, or None when
    neither is set (meaning "no restriction"). An empty set means nothing can
    match."""
    restrict: Optional[set] = None
    if status:
        restrict = set(db_operations.get_file_ids(conn, user_id, status))
    if labels:
        normalized = [_norm_label(label) for label in labels if _norm_label(label)]
        label_ids = set(db_operations.get_file_ids_by_labels(conn, user_id, normalized))
        restrict = label_ids if restrict is None else (restrict & label_ids)
    return restrict


def _prepare_filters(conn, user_id: str, status: Optional[str],
                     labels: Optional[List[str]], file_filters: dict) -> tuple:
    """Inject per-user constraints onto the file filters.

    - status / labels narrow the result to the user's matching files (via `ids`).
    - a text search (`q`) is widened so it also matches the user's labels (`or_ids`).

    Returns (filters, has_candidates). When has_candidates is False the caller
    should short-circuit with an empty result (no file can match).
    """
    filters = dict(file_filters)

    restrict = _restrict_ids(conn, user_id, status, labels)
    if restrict is not None:
        if len(restrict) == 0:
            return filters, False
        filters["ids"] = sorted(restrict)

    query_text = filters.get("q")
    if query_text:
        or_ids = db_operations.search_label_file_ids(conn, user_id, query_text)
        if or_ids:
            filters["or_ids"] = or_ids

    return filters, True


def _clip_ranked_ids(query_text: str) -> List[str]:
    """Ask the CLIP service for the most semantically similar image ids, best
    first. Raises SemanticUnavailable if the index is still building."""
    response = clients.clip_client.get(
        "search", params={"q": query_text, "limit": CLIP_CANDIDATES}
    )
    if response.status_code == 503:
        raise SemanticUnavailable()
    if response.status_code != 200:
        raise RuntimeError("clip service returned an error")
    return [row["id"] for row in response.json()["results"]]


def _meaning_candidates(conn, user_id: str, status: Optional[str],
                        labels: Optional[List[str]], file_filters: dict) -> List[dict]:
    """Resolve a meaning search into rank-ordered file items, with the user's
    status/label restriction and facet filters applied on top of the ranking."""
    query_text = (file_filters.get("q") or "").strip()
    ranked_ids = _clip_ranked_ids(query_text)
    if not ranked_ids:
        return []

    restrict = _restrict_ids(conn, user_id, status, labels)
    if restrict is not None:
        if len(restrict) == 0:
            return []
        candidate_ids = [file_id for file_id in ranked_ids if file_id in restrict]
    else:
        candidate_ids = ranked_ids

    facet_filters = {
        key: value for key, value in file_filters.items()
        if key != "q" and value
    }
    metadata = _fetch_filtered_metadata(candidate_ids, facet_filters)
    # candidate_ids is already in relevance order, so iterating it keeps rank.
    return [metadata[file_id] for file_id in candidate_ids if file_id in metadata]


def _annotate(conn, user_id: str, items: List[dict]) -> None:
    """Attach the user's tag_status + labels to each item (in place)."""
    page_ids = [item["id"] for item in items]
    status_map = db_operations.get_status_map(conn, user_id, page_ids)
    labels_map = db_operations.get_labels_map(conn, user_id, page_ids)
    for item in items:
        item["tag_status"] = status_map.get(item["id"])
        item["labels"] = labels_map.get(item["id"], [])


def query(user_id: str, status: Optional[str], labels: Optional[List[str]],
          file_filters: dict, sort: str, page: int, page_size: int,
          search_mode: str = "keyword") -> dict:
    """Gallery orchestrator: filter (status/labels/text) + annotate with the
    user's tag status and labels.

    In "meaning" mode the text query is resolved by the CLIP service into a
    relevance-ranked candidate set, which is then filtered and paginated here
    (sort is ignored — results are ordered by similarity).
    """
    conn = get_connection()
    try:
        if search_mode == "meaning" and (file_filters.get("q") or "").strip():
            items = _meaning_candidates(conn, user_id, status, labels, file_filters)
            start = (page - 1) * page_size
            page_items = items[start:start + page_size]
            _annotate(conn, user_id, page_items)
            return {
                "total": len(items),
                "page": page,
                "page_size": page_size,
                "items": page_items,
            }

        filters, has_candidates = _prepare_filters(conn, user_id, status, labels, file_filters)
        if not has_candidates:
            return {"total": 0, "page": page, "page_size": page_size, "items": []}

        params = _files_params(filters, sort, page, page_size)
        result = _files_list(params)
        _annotate(conn, user_id, result["items"])
        return result
    finally:
        conn.close()


def _records_from_items(items: List[dict], status_by_id: dict,
                        labels_by_id: Optional[dict] = None) -> List[dict]:
    """Build export rows from already-fetched file items + status/label lookups.

    `image_url` is made absolute and publicly fetchable (the gateway serves
    /images/* without auth); `status` is None for untagged files.
    """
    labels_by_id = labels_by_id or {}
    records = []
    for item in items:
        file_id = item.get("id")
        image_url = item.get("image_url")
        if image_url:
            image_url = f"{PUBLIC_BASE_URL}{image_url}"
        records.append({
            "id": file_id,
            "status": status_by_id.get(file_id),
            "labels": labels_by_id.get(file_id, []),
            "image_url": image_url,
            "dataset": item.get("dataset"),
            "split": item.get("split"),
            "captions": item.get("captions", []),
        })
    return records


def _build_records(user_id: str, file_ids: List[str], status_by_id: dict) -> List[dict]:
    """Assemble export rows for the given ids, skipping any that no longer exist."""
    metadata = _fetch_files_metadata(file_ids)
    items = [metadata[file_id] for file_id in file_ids if file_id in metadata]
    labels_by_id = _labels_for_ids(user_id, [item["id"] for item in items])
    return _records_from_items(items, status_by_id, labels_by_id)


def _status_for_ids(user_id: str, ids: List[str]) -> dict:
    """Status lookup for many ids, chunked to stay within SQLite's bind limit."""
    status_by_id: dict = {}
    conn = get_connection()
    try:
        for chunk in _chunks(ids, FILES_PAGE_LIMIT):
            status_by_id.update(db_operations.get_status_map(conn, user_id, chunk))
    finally:
        conn.close()
    return status_by_id


def _labels_for_ids(user_id: str, ids: List[str]) -> dict:
    """Label lookup for many ids, chunked to stay within SQLite's bind limit."""
    labels_by_id: dict = {}
    conn = get_connection()
    try:
        for chunk in _chunks(ids, FILES_PAGE_LIMIT):
            labels_by_id.update(db_operations.get_labels_map(conn, user_id, chunk))
    finally:
        conn.close()
    return labels_by_id


def export_filtered(user_id: str, file_filters: dict, status: Optional[str] = None,
                    labels: Optional[List[str]] = None,
                    search_mode: str = "keyword") -> List[dict]:
    """Export every file matching the given filters (status/labels/text search),
    annotated with the user's tag status and labels.

    Keyword mode pages through the files service to cover the whole matching
    set; meaning mode exports the semantic candidate set (filtered, ranked).
    """
    is_meaning = search_mode == "meaning" and bool((file_filters.get("q") or "").strip())

    if is_meaning:
        conn = get_connection()
        try:
            items = _meaning_candidates(conn, user_id, status, labels, file_filters)
        finally:
            conn.close()
    else:
        conn = get_connection()
        try:
            filters, has_candidates = _prepare_filters(conn, user_id, status, labels, file_filters)
        finally:
            conn.close()
        if not has_candidates:
            return []

        items = []
        page = 1
        while True:
            params = _files_params(filters, "id", page, FILES_PAGE_LIMIT)
            result = _files_list(params)
            page_items = result["items"]
            items.extend(page_items)
            if len(page_items) == 0 or len(items) >= result["total"]:
                break
            page += 1

    ids = [item["id"] for item in items]
    status_by_id = _status_for_ids(user_id, ids)
    labels_by_id = _labels_for_ids(user_id, ids)
    return _records_from_items(items, status_by_id, labels_by_id)


def get_tag_status(user_id: str, file_id: str) -> Optional[str]:
    """Return the user's tag status for one file, or None if untagged."""
    conn = get_connection()
    try:
        status_map = db_operations.get_status_map(conn, user_id, [file_id])
    finally:
        conn.close()
    return status_map.get(file_id)


def export(user_id: str, status: Optional[str]) -> List[dict]:
    """Build the tagged subset (optionally filtered to passed/failed) for export."""
    conn = get_connection()
    try:
        tagged = db_operations.get_tagged(conn, user_id, status)
    finally:
        conn.close()

    file_ids = [row["file_id"] for row in tagged]
    status_by_id = {row["file_id"]: row["status"] for row in tagged}
    return _build_records(user_id, file_ids, status_by_id)


def export_selected(user_id: str, file_ids: List[str]) -> List[dict]:
    """Export an explicit set of files regardless of tag (status may be None)."""
    requested = list(dict.fromkeys(file_ids))
    conn = get_connection()
    try:
        status_by_id = db_operations.get_status_map(conn, user_id, requested)
    finally:
        conn.close()
    return _build_records(user_id, requested, status_by_id)


# --- Labels -----------------------------------------------------------------

def add_label(user_id: str, file_ids: List[str], label: str) -> Optional[dict]:
    """Attach a label to files for a user (validates user + file existence).

    Returns None if the user does not exist. Missing files are skipped.
    """
    if not _user_exists(user_id):
        return None

    normalized = _norm_label(label)
    requested = list(dict.fromkeys(file_ids))
    existing = set(_fetch_files_metadata(requested).keys())
    valid = [file_id for file_id in requested if file_id in existing]
    missing = [file_id for file_id in requested if file_id not in existing]

    updated_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        for file_id in valid:
            db_operations.add_label(conn, user_id, file_id, normalized, updated_at)
        conn.commit()
    finally:
        conn.close()

    return {"labeled": len(valid), "skipped_missing": missing, "label": normalized}


def remove_label(user_id: str, file_ids: List[str], label: str) -> dict:
    normalized = _norm_label(label)
    conn = get_connection()
    try:
        removed = db_operations.remove_label(conn, user_id, file_ids, normalized)
    finally:
        conn.close()
    return {"removed": removed, "label": normalized}


def get_labels(user_id: str, file_id: str) -> List[str]:
    conn = get_connection()
    try:
        labels_map = db_operations.get_labels_map(conn, user_id, [file_id])
    finally:
        conn.close()
    return labels_map.get(file_id, [])


def label_options(user_id: str) -> List[dict]:
    conn = get_connection()
    try:
        rows = db_operations.get_label_options(conn, user_id)
    finally:
        conn.close()
    return [{"label": row["label"], "count": row["count"]} for row in rows]


def stats(user_id: str) -> dict:
    """This user's tagging + labeling summary for the statistics dashboard."""
    conn = get_connection()
    try:
        counts = db_operations.get_status_counts(conn, user_id)
        labels = db_operations.get_label_options(conn, user_id)
    finally:
        conn.close()

    passed = counts.get("passed", 0)
    failed = counts.get("failed", 0)
    return {
        "passed": passed,
        "failed": failed,
        "tagged_total": passed + failed,
        "labels": [{"label": row["label"], "count": row["count"]} for row in labels],
    }
