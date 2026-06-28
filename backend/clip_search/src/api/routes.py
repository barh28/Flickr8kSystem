"""HTTP routes for the CLIP semantic-search service.

Mounted at the root so the gateway forwards /api/clip/{action} -> /{action}.
This service is stateless w.r.t. users; the tags service calls it directly to
turn a free-text query into a ranked list of image ids.
"""
from fastapi import APIRouter, HTTPException, Query

from src.config import DEFAULT_LIMIT, MAX_LIMIT
from src.services import index

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "clip", **index.status()}


@router.get("/search")
def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
) -> dict:
    try:
        results = index.search(q, limit)
    except index.IndexNotReady:
        raise HTTPException(
            status_code=503,
            detail="Semantic index is still building; try again shortly.",
        )
    return {"query": q, "results": results}
