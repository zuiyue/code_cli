"""Image handling: read, compress, format-check, base64-encode."""

import base64
import io
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

SUPPORTED_FORMATS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_DIMENSION = 2048
MAX_SIZE_BYTES = 2 * 1024 * 1024


class ImageError(Exception):
    pass


def _validate_format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_FORMATS:
        raise ImageError(
            f"Unsupported format .{suffix}. Supported: {', '.join(SUPPORTED_FORMATS)}"
        )
    return suffix


def _compress_if_needed(data: bytes, fmt: str) -> bytes:
    if Image is None:
        return data  # no Pillow, pass through as-is

    img = Image.open(io.BytesIO(data))
    w, h = img.size
    if max(w, h) <= MAX_DIMENSION and len(data) <= MAX_SIZE_BYTES:
        return data

    # Resize if too large
    if max(w, h) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    # Compress to under MAX_SIZE
    quality = 85
    buf = io.BytesIO()
    save_fmt = "JPEG" if fmt in ("jpg", "jpeg") else fmt.upper()
    if save_fmt == "JPEG":
        img = img.convert("RGB")
    img.save(buf, format=save_fmt, quality=quality)
    return buf.getvalue()


def read_image(path: str | Path) -> tuple[str, str]:
    """Read an image file, return (base64_string, mime_type)."""
    p = Path(path)
    if not p.exists():
        raise ImageError(f"File not found: {path}")
    fmt = _validate_format(p)
    mime = f"image/{fmt}" if fmt != "jpg" else "image/jpeg"

    data = p.read_bytes()
    data = _compress_if_needed(data, fmt)
    b64 = base64.b64encode(data).decode("ascii")
    return b64, mime


def has_clipboard_image() -> bool:
    """macOS: check if clipboard contains PNG data."""
    import subprocess
    try:
        result = subprocess.run(
            ["osascript", "-e", 'clipboard info'],
            capture_output=True, text=True, timeout=5,
        )
        stdout = result.stdout or ""
        return "PNG" in stdout or "picture" in stdout
    except Exception:
        return False


def read_clipboard_image() -> tuple[str, str] | None:
    """macOS: save clipboard image to tmp, read it, return (base64, mime)."""
    import subprocess
    import tempfile
    tmp_path = Path(tempfile.mktemp(suffix=".png"))
    try:
        result = subprocess.run(
            ["osascript", "-e",
             f'set f to (POSIX file "{tmp_path}") as string\n'
             'tell application "System Events"\n'
             'set theImage to the clipboard as «class PNGf»\n'
             'set fRef to (open for access file f with write permission)\n'
             'write theImage to fRef\n'
             'close access fRef\n'
             'end tell'],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0 or not tmp_path.exists() or tmp_path.stat().st_size == 0:
            return None
        return read_image(tmp_path)
    except Exception:
        return None
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
