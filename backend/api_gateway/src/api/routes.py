"""Gateway routes: a single generic proxy + health.

`/api/{service}/{action}` is forwarded to the registered service's `/{action}`
and the upstream response is returned as-is. Images are served separately as
static files (mounted in main.py).

Auth: every endpoint except those in PUBLIC_ENDPOINTS requires a valid Bearer
token. The gateway verifies the token and injects a trusted `X-User-Id` (and
`X-Username`) header downstream, after stripping any client-supplied identity
headers so callers cannot impersonate another user.
"""
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from shared_libraries.tokens import verify_token
from src.config import PUBLIC_ENDPOINTS, REGISTRY

router = APIRouter()

# Headers we must not forward verbatim (let httpx/the upstream set their own).
_HOP_BY_HOP = {"host", "content-length", "connection", "keep-alive", "transfer-encoding"}
# Client-supplied identity/auth headers are always dropped before proxying; the
# gateway sets X-User-Id itself from the verified token (anti-spoofing).
_STRIP_REQUEST_HEADERS = _HOP_BY_HOP | {"authorization", "x-user-id", "x-username"}
# Upstream response headers worth forwarding back to the client.
_FORWARD_RESPONSE_HEADERS = {"content-disposition"}
_BEARER_PREFIX = "Bearer "


def _bearer_token(request: Request) -> Optional[str]:
    header = request.headers.get("authorization", "")
    if header.startswith(_BEARER_PREFIX):
        return header[len(_BEARER_PREFIX):].strip()
    return None


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
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in _STRIP_REQUEST_HEADERS
    }

    if (service, action) not in PUBLIC_ENDPOINTS:
        payload = verify_token(_bearer_token(request))
        if payload is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        headers["X-User-Id"] = payload["user_id"]
        headers["X-Username"] = payload.get("username", "")

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
