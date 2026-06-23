"""HTTP routes for the tags service.

Mounted at the root so the gateway can forward /api/tags/{action} -> /{action}.
"""
import csv
import io
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from src.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.schemas.tags_schema import (
    QueryResponse,
    RemoveTagsRequest,
    RemoveTagsResponse,
    SetTagsRequest,
    SetTagsResponse,
)
from src.services import tags_manager

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "tags"}


@router.post("/set", response_model=SetTagsResponse)
def set_tags(payload: SetTagsRequest) -> SetTagsResponse:
    result = tags_manager.set_tags(payload.user_id, payload.file_ids, payload.status)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.post("/remove", response_model=RemoveTagsResponse)
def remove_tags(payload: RemoveTagsRequest) -> RemoveTagsResponse:
    return tags_manager.remove_tags(payload.user_id, payload.file_ids)


@router.get("/query", response_model=QueryResponse)
def query(
    user_id: str = Query(..., min_length=1),
    status: Optional[str] = Query(None, pattern="^(passed|failed)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    q: Optional[str] = None,
    dataset: Optional[str] = None,
    length: Optional[str] = Query(None, pattern="^(short|medium|long)$"),
    split: Optional[str] = None,
    orientation: Optional[str] = Query(None, pattern="^(portrait|landscape|square)$"),
    agreement: Optional[str] = Query(None, pattern="^(high|low)$"),
    sort: str = Query("id", pattern="^(id|length|agreement|random)$"),
) -> QueryResponse:
    file_filters = {
        "q": q,
        "dataset": dataset,
        "length": length,
        "split": split,
        "orientation": orientation,
        "agreement": agreement,
    }
    return tags_manager.query(user_id, status, file_filters, sort, page, page_size)


@router.get("/export")
def export(
    user_id: str = Query(..., min_length=1),
    status: Optional[str] = Query(None, pattern="^(passed|failed)$"),
    format: str = Query("json", pattern="^(json|csv)$"),
) -> Response:
    records = tags_manager.export(user_id, status)

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "status", "dataset", "split", "captions"])
        for record in records:
            writer.writerow([
                record["id"],
                record["status"],
                record["dataset"],
                record["split"],
                " | ".join(record["captions"]),
            ])
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="tags_{user_id}.csv"'},
        )

    return JSONResponse(
        content=records,
        headers={"Content-Disposition": f'attachment; filename="tags_{user_id}.json"'},
    )
