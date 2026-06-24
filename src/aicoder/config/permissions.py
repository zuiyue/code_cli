import hashlib
import tomllib
from pathlib import Path

try:
    import tomli_w
except ImportError:
    tomli_w = None


class PermissionManager:
    def __init__(self, config_dir: Path):
        self._path = config_dir / "permissions.toml"
        self._data: dict[str, dict[str, str]] = {}
        self._load()

    def _hash_cmd(self, project_root: str, command: str) -> str:
        raw = f"{project_root}:{command}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _load(self):
        if self._path.exists():
            self._data = tomllib.loads(self._path.read_text())
            if "projects" not in self._data:
                self._data["projects"] = {}
        else:
            self._data["projects"] = {}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if tomli_w:
            with open(self._path, "wb") as f:
                tomli_w.dump(self._data, f)
        else:
            with open(self._path, "w") as f:
                f.write("[projects]\n")
                for proj, cmds in self._data.get("projects", {}).items():
                    f.write(f'\n[projects."{proj}"]\n')
                    for cmd_hash, decision in cmds.items():
                        f.write(f'"{cmd_hash}" = "{decision}"\n')

    def check(self, project_root: str, command: str) -> str | None:
        cmd_hash = self._hash_cmd(project_root, command)
        proj_root = str(Path(project_root).resolve())
        projects = self._data.get("projects", {})
        for proj_path, cmds in projects.items():
            if proj_path == proj_root:
                return cmds.get(cmd_hash)
        return None

    def save(self, project_root: str, command: str, decision: str):
        cmd_hash = self._hash_cmd(project_root, command)
        proj_root = str(Path(project_root).resolve())
        if proj_root not in self._data.get("projects", {}):
            self._data.setdefault("projects", {})[proj_root] = {}
        self._data["projects"][proj_root][cmd_hash] = decision
        self._save()
