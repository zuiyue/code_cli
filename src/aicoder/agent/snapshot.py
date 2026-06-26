"""File backup for undo support."""

import shutil
from pathlib import Path
from datetime import datetime


_snapshots: dict[str, str] = {}  # path → backup_path


def snapshot(path: str):
    """Save a backup of a file before it gets modified."""
    p = Path(path)
    if not p.exists():
        return
    backup_dir = Path.home() / ".aicoder" / "snapshots"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = backup_dir / f"{p.name}.{ts}.bak"
    shutil.copy2(p, backup)
    _snapshots[str(p)] = str(backup)


def undo(path: str) -> str | None:
    """Restore the most recent backup of a file. Returns the restored content."""
    backup = _snapshots.pop(str(Path(path)), None)
    if not backup or not Path(backup).exists():
        return None
    content = Path(backup).read_text()
    Path(path).write_text(content)
    Path(backup).unlink()
    return content


def undo_all() -> list[str]:
    """Restore all snapshotted files. Returns list of restored paths."""
    restored = []
    for path in list(_snapshots.keys()):
        if undo(path):
            restored.append(path)
    return restored


def list_snapshots() -> list[str]:
    return list(_snapshots.keys())


def clear():
    _snapshots.clear()
