"""Entry point for the CLIP semantic-search service.

Adds the service root (for `src...`) and the backend root (for
`shared_libraries...`) to sys.path so it runs both standalone and in Docker.
On startup it loads the cached embedding index, or builds it once in a
background thread (so the HTTP server is up immediately and reports progress
through /health while indexing).
"""
import os
import sys

_SERVICE_ROOT = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.dirname(_SERVICE_ROOT)
for _path in (_SERVICE_ROOT, _BACKEND_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import uvicorn
from fastapi import FastAPI

from shared_libraries.responses import register_exception_handlers
from src.api.routes import router
from src.config import HOST, PORT, SERVICE_NAME
from src.services import index


def create_app() -> FastAPI:
    app = FastAPI(title=f"{SERVICE_NAME} service")
    register_exception_handlers(app)
    index.load_or_build()
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
