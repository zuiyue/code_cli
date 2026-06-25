"""Shared constants and utility functions."""

import hashlib
from pathlib import Path

RECURSION_LIMIT = 100
RECURSION_LIMIT_KEY = "recursion_limit"
HASH_LENGTH = 12


def project_hash(project_root: str) -> str:
    return hashlib.sha256(
        str(Path(project_root).resolve()).encode()
    ).hexdigest()[:HASH_LENGTH]
