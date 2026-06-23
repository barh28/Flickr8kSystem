"""Configuration for the files service (read from environment)."""
import os

from shared_libraries.env import get_env, get_env_int

SERVICE_NAME = "files"
HOST = get_env("FILES_SERVICE_HOST", "0.0.0.0")
PORT = get_env_int("FILES_SERVICE_PORT", 8000)

DATA_DIR = get_env("DATA_DIR", "/data")
DB_PATH = get_env("FILES_DB_PATH", os.path.join(DATA_DIR, "files.db"))
IMAGES_DIR = get_env("IMAGES_DIR", os.path.join(DATA_DIR, "images"))

# Which dataset a sample belongs to. Today everything is Flickr8k, but the
# field lets us add and filter by more datasets later without schema changes.
DEFAULT_DATASET = get_env("DEFAULT_DATASET", "Flickr8k")

# Public path used to build image URLs. The gateway serves these directly as
# static files from the shared (read-only) images volume.
IMAGE_URL_PREFIX = get_env("IMAGE_URL_PREFIX", "/images")

DEFAULT_PAGE_SIZE = get_env_int("FILES_DEFAULT_PAGE_SIZE", 50)
MAX_PAGE_SIZE = get_env_int("FILES_MAX_PAGE_SIZE", 200)

# Thresholds for derived caption-length / agreement buckets (tunable).
SHORT_MAX_WORDS = get_env_int("FILES_SHORT_MAX_WORDS", 8)
MEDIUM_MAX_WORDS = get_env_int("FILES_MEDIUM_MAX_WORDS", 14)
AGREEMENT_HIGH_THRESHOLD = 0.35
