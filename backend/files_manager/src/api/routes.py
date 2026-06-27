"""HTTP routes for the files service.

Endpoints are mounted at the root so the gateway can forward
/api/files/{action} -> /{action}, and other services can call directly.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.schemas.files_schema import (
    FileItem,
    FileListResponse,
    OptionsResponse,
    StatsResponse,
)
from src.services import files_manager

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "files"}


@router.get("/list", response_model=FileListResponse)
def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    q: Optional[str] = None,
    dataset: Optional[str] = None,
    length: Optional[str] = Query(None, pattern="^(short|medium|long)$"),
    split: Optional[str] = None,
    orientation: Optional[str] = Query(None, pattern="^(portrait|landscape|square)$"),
    agreement: Optional[str] = Query(None, pattern="^(high|low)$"),
    min_agreement: Optional[float] = Query(None, ge=0, le=1),
    sort: str = Query("id", pattern="^(id|length|agreement|random)$"),
    ids: Optional[List[str]] = Query(None),
    or_ids: Optional[List[str]] = Query(None),
) -> FileListResponse:
    filters = {
        "q": q,
        "dataset": dataset,
        "length": length,
        "split": split,
        "orientation": orientation,
        "agreement": agreement,
        "min_agreement": min_agreement,
        "ids": ids,
        "or_ids": or_ids,
    }
    return files_manager.list_files(filters, sort, page, page_size)


@router.get("/get", response_model=FileItem)
def get_file(id: str = Query(..., min_length=1)) -> FileItem:
    item = files_manager.get_file(id)
    if item is None:
        raise HTTPException(status_code=404, detail="File not found")
    return item


@router.get("/options", response_model=OptionsResponse)
def options() -> OptionsResponse:
    return files_manager.get_options()


@router.get("/stats", response_model=StatsResponse)
def stats(dataset: Optional[str] = None) -> StatsResponse:
    return files_manager.get_stats(dataset)
