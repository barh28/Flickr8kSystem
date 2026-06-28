"""Configuration for the tags service (read from environment)."""
import os

from shared_libraries.env import get_env, get_env_int

SERVICE_NAME = "tags"
HOST = get_env("TAGS_SERVICE_HOST", "0.0.0.0")
PORT = get_env_int("TAGS_SERVICE_PORT", 8000)

DATA_DIR = get_env("DATA_DIR", "/data")
DB_PATH = get_env("TAGS_DB_PATH", os.path.join(DATA_DIR, "tags.db"))

# Direct service-to-service URLs (no gateway hop).
USERS_SERVICE_URL = get_env("USERS_SERVICE_URL", "http://users:8000")
FILES_SERVICE_URL = get_env("FILES_SERVICE_URL", "http://files:8000")
CLIP_SERVICE_URL = get_env("CLIP_SERVICE_URL", "http://clip:8000")

# How many top semantic matches the CLIP service returns before facet/tag
# filters are applied on top. Bounds the candidate set for meaning search.
CLIP_CANDIDATES = get_env_int("CLIP_CANDIDATES", 500)

DEFAULT_PAGE_SIZE = get_env_int("TAGS_DEFAULT_PAGE_SIZE", 50)
MAX_PAGE_SIZE = get_env_int("TAGS_MAX_PAGE_SIZE", 200)

# Public base URL of the gateway, used to build absolute (publicly fetchable)
# image URLs in exports. The images themselves are public static assets; only
# user tag data is access-controlled. Override per-deployment.
PUBLIC_BASE_URL = get_env("PUBLIC_BASE_URL", "http://localhost:8080").rstrip("/")

# Max ids per call to files/list (mirrors the files service MAX_PAGE_SIZE).
FILES_PAGE_LIMIT = get_env_int("FILES_PAGE_LIMIT", 200)
