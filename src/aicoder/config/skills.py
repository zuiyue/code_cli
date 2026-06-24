import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SkillInfo:
    name: str
    source: str  # "builtin", "user", "project"
    path: str
    description: str


def _parse_skill_md(path: Path) -> dict | None:
    """Parse SKILL.md YAML frontmatter. Returns dict with name, description or None."""
    if not path.exists():
        return None
    content = path.read_text()
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 2:
        return None
    try:
        return yaml.safe_load(parts[1])
    except Exception:
        return {"name": path.parent.name, "description": ""}


def _scan_dir(directory: Path, source: str) -> list[SkillInfo]:
    if not directory.exists():
        return []
    results = []
    for item in sorted(directory.iterdir()):
        if item.is_dir():
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
        """Scan all three sources. Project skills override user, which override builtin."""
        seen: dict[str, SkillInfo] = {}

        # Builtin (lowest priority)
        for s in _scan_dir(self._builtin_dir, "builtin"):
            seen[s.name] = s

        # User (medium priority)
        for s in _scan_dir(self._user_dir, "user"):
            seen[s.name] = s

        # Project (highest priority)
        proj_skills = Path(project_root) / "skills"
        for s in _scan_dir(proj_skills, "project"):
            seen[s.name] = s

        return sorted(seen.values(), key=lambda s: (s.source, s.name))

    def resolve_paths(self, project_root: str = ".") -> list[str]:
        """Return existing skill directory paths for agent initialization."""
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
        """Clone a skill repo into user skills directory. Returns (success, message)."""
        self._user_dir.mkdir(parents=True, exist_ok=True)

        # Extract repo name from URL
        name = git_url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        dest = self._user_dir / name

        if dest.exists():
            return False, f"Skill '{name}' already exists at {dest}"

        result = subprocess.run(
            ["git", "clone", git_url, str(dest)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            err = result.stderr.strip().split("\n")[-1] if result.stderr else "clone failed"
            return False, f"Clone failed: {err}"

        # Validate SKILL.md
        skill_md = dest / "SKILL.md"
        if not skill_md.exists():
            shutil.rmtree(dest, ignore_errors=True)
            return False, "Repository has no SKILL.md at root"

        meta = _parse_skill_md(skill_md)
        if not meta:
            shutil.rmtree(dest, ignore_errors=True)
            return False, "SKILL.md has invalid format (missing YAML frontmatter)"

        skill_name = meta.get("name", name)
        return True, f"Installed '{skill_name}' from {git_url}"

    def remove(self, name: str) -> tuple[bool, str]:
        """Remove a user-installed skill. Returns (success, message)."""
        target = self._user_dir / name
        if not target.exists():
            # Try matching by SKILL.md name field
            for d in self._user_dir.iterdir():
                if d.is_dir():
                    meta = _parse_skill_md(d / "SKILL.md")
                    if meta and meta.get("name") == name:
                        target = d
                        break
            else:
                return False, f"Skill '{name}' not found in user skills"

        shutil.rmtree(target)
        return True, f"Removed '{name}'"

    def get_skill(self, name: str, project_root: str = ".") -> SkillInfo | None:
        """Get a single skill by name."""
        for s in self.discover(project_root):
            if s.name == name:
                return s
        return None

    def read_skill_md(self, name: str, project_root: str = ".") -> str | None:
        """Read the full SKILL.md content for a skill."""
        info = self.get_skill(name, project_root)
        if not info:
            return None
        path = Path(info.path) / "SKILL.md"
        if path.exists():
            return path.read_text()
        return None
