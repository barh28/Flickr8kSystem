"""Minimal HTTP client for direct service-to-service calls.

Services call each other directly (not through the gateway). Each target
service's base URL is provided via an environment variable, e.g.
FILES_SERVICE_URL / USERS_SERVICE_URL, and passed in here.
"""
from typing import Optional

import httpx


class ServiceClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def get(self, path: str, params: Optional[dict] = None) -> httpx.Response:
        return httpx.get(self._url(path), params=params, timeout=self.timeout)

    def post(self, path: str, json: Optional[dict] = None) -> httpx.Response:
        return httpx.post(self._url(path), json=json, timeout=self.timeout)
