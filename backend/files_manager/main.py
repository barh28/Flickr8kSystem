"""Entry point for the files service.

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

import uvicorn
from fastapi import FastAPI

from shared_libraries.responses import register_exception_handlers
from src.api.routes import router
from src.config import HOST, PORT, SERVICE_NAME
from src.db.connection import init_db


def create_app() -> FastAPI:
    app = FastAPI(title=f"{SERVICE_NAME} service")
    register_exception_handlers(app)
    init_db()
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
