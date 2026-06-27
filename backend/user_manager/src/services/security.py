"""Password hashing helpers (standard library only).

We never store the plaintext password. We store a salted PBKDF2-HMAC-SHA256
digest encoded as `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`, which keeps
the algorithm parameters next to the hash so verification is self-contained.
"""
import hashlib
import hmac
import os

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 100_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False
    parts = stored.split("$")
    if len(parts) != 4:
        return False
    algorithm = parts[0]
    iterations_text = parts[1]
    salt_hex = parts[2]
    expected_hex = parts[3]
    if algorithm != _ALGORITHM:
        return False
    try:
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest, expected)
