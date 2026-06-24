import hashlib
import tomllib
import tomli_w
from pathlib import Path


class PermissionManager:
    def __init__(self, config_dir: Path):
        self._path = config_dir / "permissions.toml"
        self._data: dict[str, dict[str, str]] = {}
        self._load()

    def _hash_cmd(self, project_root: str, command: str) -> str:
        resolved = str(Path(project_root).resolve())
        raw = f"{resolved}:{command}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _load(self):
        self._data = {"projects": {}}
        if not self._path.exists():
            return
        try:
            self._data = tomllib.loads(self._path.read_text())
        except (tomllib.TOMLDecodeError, OSError):
            self._data = {"projects": {}}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "wb") as f:
            tomli_w.dump(self._data, f)

    def check(self, project_root: str, command: str) -> str | None:
        cmd_hash = self._hash_cmd(project_root, command)
        proj_root = str(Path(project_root).resolve())
        return self._data.get("projects", {}).get(proj_root, {}).get(cmd_hash)

    def save(self, project_root: str, command: str, decision: str):
        cmd_hash = self._hash_cmd(project_root, command)
        proj_root = str(Path(project_root).resolve())
        self._data.setdefault("projects", {}).setdefault(proj_root, {})[cmd_hash] = decision
        self._save()
