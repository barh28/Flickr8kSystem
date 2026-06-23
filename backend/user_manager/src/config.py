"""Configuration for the users service (read from environment)."""
import os

from shared_libraries.env import get_env, get_env_int

SERVICE_NAME = "users"
HOST = get_env("USER_SERVICE_HOST", "0.0.0.0")
PORT = get_env_int("USER_SERVICE_PORT", 8000)

DATA_DIR = get_env("DATA_DIR", "/data")
DB_PATH = get_env("USER_DB_PATH", os.path.join(DATA_DIR, "users.db"))
