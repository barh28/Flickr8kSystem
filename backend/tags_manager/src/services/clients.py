"""Direct clients to the other services (no gateway hop)."""
from shared_libraries.http_client import ServiceClient
from src.config import FILES_SERVICE_URL, USERS_SERVICE_URL

users_client = ServiceClient(USERS_SERVICE_URL)
files_client = ServiceClient(FILES_SERVICE_URL)
