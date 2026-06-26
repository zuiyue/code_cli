"""Project initialization — analyze project and generate AGENTS.md."""

import os
from pathlib import Path


def analyze_project(project_root: str) -> str:
    """Scan project and generate an AGENTS.md content string."""
    root = Path(project_root).resolve()
    lines = [f"# {root.name}", ""]

    # Detect language/tech from config files
    tech = _detect_tech(root)
    if tech["language"]:
        lines.append(f"**Language:** {tech['language']}")
    if tech["framework"]:
        lines.append(f"**Framework:** {tech['framework']}")
    if tech["build"]:
        lines.append(f"**Build:** {tech['build']}")
    lines.append("")

    # Build commands
    cmds = _detect_commands(root, tech)
    if cmds:
        lines.append("## Commands")
        lines.append("")
        for label, cmd in cmds.items():
            lines.append(f"- **{label}:** `{cmd}`")
        lines.append("")

    # Directory structure
    tree = _dir_tree(root, max_depth=3)
    if tree:
        lines.append("## Structure")
        lines.append("")
        lines.append("```")
        lines.extend(tree)
        lines.append("```")
        lines.append("")

    # Conventions
    conventions = _detect_conventions(root, tech)
    if conventions:
        lines.append("## Conventions")
        lines.append("")
        for c in conventions:
            lines.append(f"- {c}")
        lines.append("")

    # Git info
    lines.append("## Instructions")
    lines.append("")
    lines.append("Always read relevant files before making changes.")
    lines.append("Run tests after each change. Commit with conventional commits (feat:/fix:/refactor:).")
    if tech.get("test_command"):
        lines.append(f"Test with: `{tech['test_command']}`")

    return "\n".join(lines)


def _detect_tech(root: Path) -> dict:
    """Detect tech stack from project files."""
    result = {"language": "", "framework": "", "build": "", "test_command": ""}

    if (root / "pyproject.toml").exists():
        content = (root / "pyproject.toml").read_text()
        result["language"] = "Python"
        result["build"] = "hatchling/pip"
        if "pytest" in content:
            result["test_command"] = "pytest tests/"
        if "fastapi" in content.lower():
            result["framework"] = "FastAPI"
        elif "flask" in content.lower():
            result["framework"] = "Flask"
        elif "django" in content.lower():
            result["framework"] = "Django"

    elif (root / "package.json").exists():
        import json
        try:
            pkg = json.loads((root / "package.json").read_text())
            result["language"] = "TypeScript" if "typescript" in str(pkg).lower() else "JavaScript"
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps: result["framework"] = "Next.js"
            elif "react" in deps: result["framework"] = "React"
            elif "vue" in deps: result["framework"] = "Vue"
            if "jest" in deps: result["test_command"] = "npm test"
            elif "vitest" in deps: result["test_command"] = "npx vitest"
            result["build"] = "npm/npx"
        except Exception:
            result["language"] = "Node.js"

    elif (root / "go.mod").exists():
        result["language"] = "Go"
        result["build"] = "go build"
        result["test_command"] = "go test ./..."

    elif (root / "Cargo.toml").exists():
        result["language"] = "Rust"
        result["build"] = "cargo"
        result["test_command"] = "cargo test"

    elif (root / "pom.xml").exists():
        result["language"] = "Java"
        result["build"] = "Maven"
        result["test_command"] = "mvn test"

    elif (root / "Makefile").exists():
        result["build"] = "make"

    return result


def _detect_commands(root: Path, tech: dict) -> dict:
    """Detect common build/test/lint commands."""
    cmds = {}
    if tech.get("test_command"):
        cmds["Test"] = tech["test_command"]

    if (root / "Makefile").exists():
        content = (root / "Makefile").read_text()
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("install:"):
                cmds["Install"] = "make install"
            elif line.startswith("build:"):
                cmds["Build"] = "make build"
            elif line.startswith("lint:"):
                cmds["Lint"] = "make lint"

    if not cmds.get("Install"):
        if (root / "pyproject.toml").exists():
            cmds["Install"] = "pip install -e ."
        elif (root / "package.json").exists():
            cmds["Install"] = "npm install"

    return cmds


def _dir_tree(root: Path, max_depth: int = 3, prefix: str = "") -> list[str]:
    """Generate a simplified directory tree."""
    lines = []
    try:
        entries = sorted(
            [e for e in root.iterdir()
             if not e.name.startswith(".")
             and e.name not in ("node_modules", "__pycache__", ".pytest_cache",
                                "dist", "build", ".git", "venv", ".venv")],
            key=lambda e: (e.is_file(), e.name)
        )
    except PermissionError:
        return []

    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            if max_depth > 1:
                extension = "    " if i == len(entries) - 1 else "│   "
                lines.extend(_dir_tree(entry, max_depth - 1, prefix + extension))
        else:
            lines.append(f"{prefix}{connector}{entry.name}")
    return lines


def _detect_conventions(root: Path, tech: dict) -> list[str]:
    """Detect coding conventions from config files."""
    conventions = []

    if tech["language"] == "Python":
        if (root / "pyproject.toml").exists():
            content = (root / "pyproject.toml").read_text()
            if "ruff" in content:
                conventions.append("Ruff is used for linting and formatting")
            if "mypy" in content:
                conventions.append("MyPy strict type checking enabled")
            if "pytest" in content:
                conventions.append("Tests use pytest")
        conventions.append("Python 3.11+ syntax (use pathlib, f-strings, type hints)")

    elif tech["language"] in ("TypeScript", "JavaScript"):
        if (root / ".eslintrc.json").exists() or (root / ".eslintrc.js").exists():
            conventions.append("ESLint configured")
        if (root / ".prettierrc").exists():
            conventions.append("Prettier formatting")

    # Check git config
    if (root / ".gitignore").exists() and "work/" in (root / ".gitignore").read_text():
        conventions.append("work/ directory is gitignored (temp files)")

    return conventions
