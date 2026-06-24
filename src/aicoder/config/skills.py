import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SkillInfo:
    name: str
    source: str
    path: str
    description: str


def _parse_skill_md(path: Path) -> dict | None:
    if not path.exists():
        return None
    content = path.read_text()
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 2:
        return None
    try:
        parsed = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(parsed, dict):
        return {"name": path.parent.name, "description": ""}
    return parsed


def _scan_dir(directory: Path, source: str) -> list[SkillInfo]:
    if not directory.exists():
        return []
    results = []
    for item in sorted(directory.iterdir()):
        if not item.is_dir():
            continue
        skill_md = item / "SKILL.md"
        meta = _parse_skill_md(skill_md)
        if meta:
            results.append(SkillInfo(
                name=meta.get("name", item.name),
                source=source,
                path=str(item),
                description=meta.get("description", ""),
            ))
    return results


class SkillManager:
    def __init__(self, config_dir: Path, package_dir: Path):
        self._user_dir = config_dir / "skills"
        self._builtin_dir = package_dir / "skills" / "builtin"

    def discover(self, project_root: str = ".") -> list[SkillInfo]:
        seen: dict[str, SkillInfo] = {}
        for s in _scan_dir(self._builtin_dir, "builtin"):
            seen[s.name] = s
        for s in _scan_dir(self._user_dir, "user"):
            seen[s.name] = s
        for s in _scan_dir(Path(project_root) / "skills", "project"):
            seen[s.name] = s
        return sorted(seen.values(), key=lambda s: (s.source, s.name))

    def resolve_paths(self, project_root: str = ".") -> list[str]:
        paths = []
        if self._builtin_dir.exists():
            paths.append(str(self._builtin_dir))
        if self._user_dir.exists():
            paths.append(str(self._user_dir))
        proj = Path(project_root) / "skills"
        if proj.exists():
            paths.append(str(proj))
        return paths

    def install(self, git_url: str) -> tuple[bool, str]:
        self._user_dir.mkdir(parents=True, exist_ok=True)
        name = git_url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        dest = self._user_dir / name

        if dest.exists():
            return False, f"Skill '{name}' already exists at {dest}"

        try:
            result = subprocess.run(
                ["git", "clone", git_url, str(dest)],
                capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            shutil.rmtree(dest, ignore_errors=True)
            return False, "Clone timed out (120s)"

        if result.returncode != 0:
            shutil.rmtree(dest, ignore_errors=True)
            err = result.stderr.strip().split("\n")[-1] if result.stderr else "clone failed"
            return False, f"Clone failed: {err}"

        skill_md = dest / "SKILL.md"
        if not skill_md.exists():
            shutil.rmtree(dest, ignore_errors=True)
            return False, "Repository has no SKILL.md at root"

        meta = _parse_skill_md(skill_md)
        if not meta or not meta.get("name"):
            shutil.rmtree(dest, ignore_errors=True)
            return False, "SKILL.md has invalid format (missing YAML frontmatter with name)"

        return True, f"Installed '{meta['name']}' from {git_url}"

    def remove(self, name: str) -> tuple[bool, str]:
        target = self._user_dir / name
        if not target.exists() or not target.is_dir():
            for d in self._user_dir.iterdir():
                if d.is_dir():
                    meta = _parse_skill_md(d / "SKILL.md")
                    if meta and meta.get("name") == name:
                        target = d
                        break
            else:
                return False, f"Skill '{name}' not found in user skills"

        try:
            shutil.rmtree(target)
        except OSError as e:
            return False, f"Failed to remove '{name}': {e}"
        return True, f"Removed '{name}'"

    def get_skill(self, name: str, project_root: str = ".") -> SkillInfo | None:
        for s in self.discover(project_root):
            if s.name == name:
                return s
        return None

    def read_skill_md(self, name: str, project_root: str = ".") -> str | None:
        info = self.get_skill(name, project_root)
        if not info:
            return None
        path = Path(info.path) / "SKILL.md"
        if path.exists():
            return path.read_text()
        return None
