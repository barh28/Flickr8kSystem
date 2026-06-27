"""Configuration for the API gateway (read from environment).

The gateway is the single entry point. The REGISTRY maps a service name to its
base URL; adding a new service later is just one entry here, no route changes.
"""
import os

from shared_libraries.env import get_env, get_env_int

SERVICE_NAME = "gateway"
HOST = get_env("GATEWAY_HOST", "0.0.0.0")
PORT = get_env_int("GATEWAY_PORT", 8080)

DATA_DIR = get_env("DATA_DIR", "/data")
IMAGES_DIR = get_env("IMAGES_DIR", os.path.join(DATA_DIR, "images"))

REGISTRY = {
    "users": get_env("USERS_SERVICE_URL", "http://users:8000"),
    "files": get_env("FILES_SERVICE_URL", "http://files:8000"),
    "tags": get_env("TAGS_SERVICE_URL", "http://tags:8000"),
}

PROXY_TIMEOUT = float(get_env("PROXY_TIMEOUT", "30"))

# (service, action) pairs reachable without a token. Everything else requires a
# valid Bearer token, from which the gateway injects a trusted X-User-Id.
PUBLIC_ENDPOINTS = {
    ("users", "create"),
    ("users", "login"),
}

_CORS_RAW = get_env("CORS_ORIGINS", "*")
CORS_ORIGINS = ["*"] if _CORS_RAW == "*" else [origin.strip() for origin in _CORS_RAW.split(",") if origin.strip()]
