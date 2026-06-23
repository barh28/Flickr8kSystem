"""Gateway routes: a single generic proxy + health.

`/api/{service}/{action}` is forwarded to the registered service's `/{action}`
and the upstream response is returned as-is. Images are served separately as
static files (mounted in main.py).
"""
import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from src.config import REGISTRY

router = APIRouter()

# Headers we must not forward verbatim (let httpx/the upstream set their own).
_HOP_BY_HOP = {"host", "content-length", "connection", "keep-alive", "transfer-encoding"}
# Upstream response headers worth forwarding back to the client.
_FORWARD_RESPONSE_HEADERS = {"content-disposition"}


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "gateway", "services": sorted(REGISTRY.keys())}


@router.api_route("/api/{service}/{action}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(service: str, action: str, request: Request) -> Response:
    base_url = REGISTRY.get(service)
    if base_url is None:
        raise HTTPException(status_code=404, detail=f"Unknown service '{service}'")

    url = f"{base_url.rstrip('/')}/{action}"
    body = await request.body()
    headers = {key: value for key, value in request.headers.items() if key.lower() not in _HOP_BY_HOP}

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        upstream = await client.request(
            request.method,
            url,
            params=request.query_params.multi_items(),
            content=body,
            headers=headers,
        )
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail=f"Service '{service}' is unavailable")

    forwarded = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() in _FORWARD_RESPONSE_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
        headers=forwarded,
    )
