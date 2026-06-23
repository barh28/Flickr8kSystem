"""Tiny helpers for reading configuration from environment variables.

Shared by all services so env handling is written once.
"""
import os
from typing import Optional


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def get_env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)
