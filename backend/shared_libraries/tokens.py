"""Stateless signed tokens shared by the users service (mint) and the gateway
(verify). This mimics a JWT with the standard library only.

A token is `<payload_b64>.<signature_b64>` where the signature is
HMAC-SHA256(payload_b64, AUTH_SECRET). Because it is signed, the gateway can
trust the identity inside it without any DB lookup or call to the users service.

Note: this is a lightweight mimic for the assignment (no refresh tokens, no key
rotation). The secret must be identical in every service that mints/verifies.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from shared_libraries.env import get_env, get_env_int

_SECRET = get_env("AUTH_SECRET", "dev-insecure-secret-change-me")
_DEFAULT_TTL_SECONDS = get_env_int("AUTH_TOKEN_TTL_SECONDS", 86400)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _sign(payload_b64: str) -> str:
    signature = hmac.new(_SECRET.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256)
    return _b64encode(signature.digest())


def create_token(user_id: str, username: str, ttl_seconds: Optional[int] = None) -> str:
    ttl = _DEFAULT_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    now = int(time.time())
    payload = {"user_id": user_id, "username": username, "iat": now, "exp": now + ttl}
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{payload_b64}.{_sign(payload_b64)}"


def verify_token(token: str) -> Optional[dict]:
    """Return the payload dict if the token is valid and unexpired, else None."""
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 2:
        return None
    payload_b64 = parts[0]
    signature = parts[1]
    if not hmac.compare_digest(signature, _sign(payload_b64)):
        return None
    try:
        payload = json.loads(_b64decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        return None
    expires_at = payload.get("exp")
    if expires_at is not None and int(time.time()) > int(expires_at):
        return None
    return payload
