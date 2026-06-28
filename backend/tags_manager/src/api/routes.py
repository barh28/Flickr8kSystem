"""HTTP routes for the tags service.

Mounted at the root so the gateway can forward /api/tags/{action} -> /{action}.
"""
import csv
import io
import json
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from src.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.schemas.tags_schema import (
    AddLabelResponse,
    ExportSelectedRequest,
    LabelOptionsResponse,
    LabelRequest,
    LabelsResponse,
    QueryResponse,
    RemoveLabelResponse,
    RemoveTagsRequest,
    RemoveTagsResponse,
    SetTagsRequest,
    SetTagsResponse,
    TagsStatsResponse,
)
from src.services import tags_manager

router = APIRouter()

# Identity is set by the gateway from the verified token; clients never send it.
_USER_ID_HEADER = Header(..., alias="X-User-Id", min_length=1)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "tags"}


@router.post("/set", response_model=SetTagsResponse)
def set_tags(payload: SetTagsRequest, user_id: str = _USER_ID_HEADER) -> SetTagsResponse:
    result = tags_manager.set_tags(user_id, payload.file_ids, payload.status)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.post("/remove", response_model=RemoveTagsResponse)
def remove_tags(payload: RemoveTagsRequest, user_id: str = _USER_ID_HEADER) -> RemoveTagsResponse:
    return tags_manager.remove_tags(user_id, payload.file_ids)


@router.get("/status")
def tag_status(
    file_id: str = Query(..., min_length=1),
    user_id: str = _USER_ID_HEADER,
) -> dict:
    return {"file_id": file_id, "status": tags_manager.get_tag_status(user_id, file_id)}


@router.post("/label_add", response_model=AddLabelResponse)
def label_add(payload: LabelRequest, user_id: str = _USER_ID_HEADER) -> AddLabelResponse:
    result = tags_manager.add_label(user_id, payload.file_ids, payload.label)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.post("/label_remove", response_model=RemoveLabelResponse)
def label_remove(payload: LabelRequest, user_id: str = _USER_ID_HEADER) -> RemoveLabelResponse:
    return tags_manager.remove_label(user_id, payload.file_ids, payload.label)


@router.get("/labels", response_model=LabelsResponse)
def labels(file_id: str = Query(..., min_length=1), user_id: str = _USER_ID_HEADER) -> LabelsResponse:
    return {"file_id": file_id, "labels": tags_manager.get_labels(user_id, file_id)}


@router.get("/label_options", response_model=LabelOptionsResponse)
def label_options(user_id: str = _USER_ID_HEADER) -> LabelOptionsResponse:
    return {"labels": tags_manager.label_options(user_id)}


@router.get("/stats", response_model=TagsStatsResponse)
def stats(user_id: str = _USER_ID_HEADER) -> TagsStatsResponse:
    return tags_manager.stats(user_id)


@router.get("/query", response_model=QueryResponse)
def query(
    user_id: str = _USER_ID_HEADER,
    status: Optional[str] = Query(None, pattern="^(passed|failed)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    q: Optional[str] = None,
    dataset: Optional[str] = None,
    length: Optional[str] = Query(None, pattern="^(short|medium|long)$"),
    split: Optional[str] = None,
    orientation: Optional[str] = Query(None, pattern="^(portrait|landscape|square)$"),
    agreement: Optional[str] = Query(None, pattern="^(high|low)$"),
    min_agreement: Optional[float] = Query(None, ge=0, le=1),
    labels: Optional[List[str]] = Query(None),
    sort: str = Query("id", pattern="^(id|length|agreement|random)$"),
    search_mode: str = Query("keyword", pattern="^(keyword|meaning)$"),
) -> QueryResponse:
    file_filters = {
        "q": q,
        "dataset": dataset,
        "length": length,
        "split": split,
        "orientation": orientation,
        "agreement": agreement,
        "min_agreement": min_agreement,
    }
    try:
        return tags_manager.query(
            user_id, status, labels, file_filters, sort, page, page_size, search_mode
        )
    except tags_manager.SemanticUnavailable:
        raise HTTPException(
            status_code=503,
            detail="Semantic index is still building; try again shortly.",
        )


def _download(content: str, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _report_response(records: list, fmt: str, stem: str) -> Response:
    """Human-facing annotation report: status + labels + content. Round-trips
    back through bulk tagging."""
    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "status", "labels", "image_url", "dataset", "split", "captions"])
        for record in records:
            writer.writerow([
                record["id"],
                record["status"],
                " | ".join(record.get("labels", [])),
                record["image_url"],
                record["dataset"],
                record["split"],
                " | ".join(record["captions"]),
            ])
        return _download(buffer.getvalue(), "text/csv", f"{stem}.csv")

    return JSONResponse(
        content=records,
        headers={"Content-Disposition": f'attachment; filename="{stem}.json"'},
    )


def _training_response(records: list, fmt: str, stem: str) -> Response:
    """ML-ready manifest: image reference + captions (+ split). Triage metadata
    (status / user labels) is dropped so it can feed a training pipeline as-is.

    - jsonl: one image per line -> {image, image_url, split, captions}
    - csv:   one row per (image, caption) pair (exploded), the classic layout
    """
    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["image", "image_url", "split", "caption"])
        for record in records:
            for caption in record["captions"]:
                writer.writerow([record["id"], record["image_url"], record["split"], caption])
        return _download(buffer.getvalue(), "text/csv", f"{stem}.csv")

    # JSONL (newline-delimited JSON), the default training format.
    lines = []
    for record in records:
        lines.append(json.dumps({
            "image": record["id"],
            "image_url": record["image_url"],
            "split": record["split"],
            "captions": record["captions"],
        }))
    return _download("\n".join(lines) + "\n", "application/x-ndjson", f"{stem}.jsonl")


def _export_response(records: list, fmt: str, stem: str, purpose: str = "report") -> Response:
    if purpose == "training":
        return _training_response(records, fmt, stem)
    return _report_response(records, fmt, stem)


@router.get("/export")
def export(
    user_id: str = _USER_ID_HEADER,
    status: Optional[str] = Query(None, pattern="^(passed|failed)$"),
    format: str = Query("json", pattern="^(json|csv)$"),
) -> Response:
    records = tags_manager.export(user_id, status)
    stem = f"tags_{status}" if status else "tags_all"
    return _export_response(records, format, stem)


@router.post("/export_selected")
def export_selected(
    payload: ExportSelectedRequest,
    user_id: str = _USER_ID_HEADER,
    format: str = Query("json", pattern="^(json|jsonl|csv)$"),
    purpose: str = Query("report", pattern="^(report|training)$"),
) -> Response:
    records = tags_manager.export_selected(user_id, payload.file_ids)
    stem = "training_selected" if purpose == "training" else "selected"
    return _export_response(records, format, stem, purpose)


@router.get("/export_filtered")
def export_filtered(
    user_id: str = _USER_ID_HEADER,
    q: Optional[str] = None,
    dataset: Optional[str] = None,
    length: Optional[str] = Query(None, pattern="^(short|medium|long)$"),
    split: Optional[str] = None,
    orientation: Optional[str] = Query(None, pattern="^(portrait|landscape|square)$"),
    agreement: Optional[str] = Query(None, pattern="^(high|low)$"),
    min_agreement: Optional[float] = Query(None, ge=0, le=1),
    status: Optional[str] = Query(None, pattern="^(passed|failed)$"),
    labels: Optional[List[str]] = Query(None),
    format: str = Query("json", pattern="^(json|jsonl|csv)$"),
    purpose: str = Query("report", pattern="^(report|training)$"),
    search_mode: str = Query("keyword", pattern="^(keyword|meaning)$"),
) -> Response:
    file_filters = {
        "q": q,
        "dataset": dataset,
        "length": length,
        "split": split,
        "orientation": orientation,
        "agreement": agreement,
        "min_agreement": min_agreement,
    }
    try:
        records = tags_manager.export_filtered(user_id, file_filters, status, labels, search_mode)
    except tags_manager.SemanticUnavailable:
        raise HTTPException(
            status_code=503,
            detail="Semantic index is still building; try again shortly.",
        )
    prefix = "training" if purpose == "training" else "files"
    stem = f"{prefix}_{split}" if split else f"{prefix}_filtered"
    return _export_response(records, format, stem, purpose)
