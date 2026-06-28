"""Direct clients to the other services (no gateway hop)."""
from shared_libraries.http_client import ServiceClient
from src.config import CLIP_SERVICE_URL, FILES_SERVICE_URL, USERS_SERVICE_URL

users_client = ServiceClient(USERS_SERVICE_URL)
files_client = ServiceClient(FILES_SERVICE_URL)
# Indexing the first time can be slow to *load*, but search itself is fast; a
# generous timeout avoids spurious failures right after startup.
clip_client = ServiceClient(CLIP_SERVICE_URL, timeout=30.0)
