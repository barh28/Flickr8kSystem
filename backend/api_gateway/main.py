"""Entry point for the API gateway.

Adds the service root (for `src...`) and the backend root (for
`shared_libraries...`) to sys.path so the service runs both standalone
(local dev) and inside Docker.
"""
import os
import sys

_SERVICE_ROOT = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.dirname(_SERVICE_ROOT)
for _path in (_SERVICE_ROOT, _BACKEND_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shared_libraries.responses import register_exception_handlers
from src.api.routes import router
from src.config import CORS_ORIGINS, HOST, IMAGES_DIR, PORT, PROXY_TIMEOUT, SERVICE_NAME


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=PROXY_TIMEOUT)
    try:
        yield
    finally:
        await app.state.http_client.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title=f"{SERVICE_NAME} service", lifespan=lifespan)
    register_exception_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    # Serve dataset images directly from the shared (read-only) volume.
    os.makedirs(IMAGES_DIR, exist_ok=True)
    app.mount("/images", StaticFiles(directory=IMAGES_DIR, check_dir=False), name="images")
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
