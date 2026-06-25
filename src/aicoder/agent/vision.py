"""Vision module: standalone multimodal image processing and model selection.

All functions are self-contained and testable without REPL dependencies.
"""

import os
from pathlib import Path


class ImageAttachment:
    """Encoded image ready for multimodal message."""
    def __init__(self, b64: str, mime: str, source: str = ""):
        self.base64 = b64
        self.mime = mime
        self.source = source or ""

    @property
    def size_kb(self) -> int:
        return len(self.base64) // 1024

    def build_message(self, text: str = "") -> dict:
        return {
            "role": "user",
            "content": [
                {"type": "text", "text": text or "Analyze this image"},
                {"type": "image_url", "image_url": {
                    "url": f"data:{self.mime};base64,{self.base64}"
                }},
            ],
        }


def pick_vision_model() -> str | None:
    """Return the first vision model with an available API key."""
    from aicoder.agent.models import MODEL_REGISTRY
    for name, info in MODEL_REGISTRY.items():
        if not info.get("vision"):
            continue
        env_key = info.get("env_key", "")
        if env_key and os.environ.get(env_key):
            return name
    return None


def describe_model(name: str) -> str:
    """Return human-readable model description."""
    from aicoder.agent.models import get_model_info
    info = get_model_info(name)
    return info["display"] if info else name


def supports_vision(name: str) -> bool:
    """Check if a model supports vision/image analysis."""
    from aicoder.agent.models import supports_vision as _sv
    return _sv(name)
