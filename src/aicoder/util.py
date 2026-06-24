"""Shared constants and utility functions."""

import hashlib
from pathlib import Path

RECURSION_LIMIT = 100
RECURSION_LIMIT_KEY = "recursion_limit"
HASH_LENGTH = 12
PERMISSION_HASH_LENGTH = 16
MAX_OUTPUT_LINES = 500
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_MODEL_NAME = "aicoder"


def project_hash(project_root: str) -> str:
    return hashlib.sha256(
        str(Path(project_root).resolve()).encode()
    ).hexdigest()[:HASH_LENGTH]
