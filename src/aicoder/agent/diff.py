"""File diff preview for write_file/edit_file confirmation — opencode-style."""

import difflib
from pathlib import Path

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax


_console = Console()


def show_diff(path: str, new_content: str, max_lines: int = 60) -> str:
    """Show a git-style unified diff between existing file and new content.

    Uses rich for color: green additions, red deletions, bold headers.
    Returns empty string if output was rendered (calling print directly),
    or a plain string for tests.
    """
    p = Path(path)

    if not p.exists():
        return _show_new_file(path, new_content)

    old = p.read_text()
    old_lines = old.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    ))

    if not diff_lines:
        return "  (no changes)"

    # Truncate if too long
    total = len(diff_lines)
    if total > max_lines:
        diff_lines = diff_lines[:max_lines]
        diff_lines.append(f"... ({total - max_lines} more lines)")

    # Render with rich colors
    text = Text()
    for i, line in enumerate(diff_lines):
        if line.startswith("---") or line.startswith("+++"):
            text.append(line, style="bold")
        elif line.startswith("@@"):
            text.append(line, style="bold cyan")
        elif line.startswith("+"):
            text.append(line, style="green")
        elif line.startswith("-"):
            text.append(line, style="red")
        else:
            text.append(line, style="dim")
        text.append("\n")

    _console.print()
    _console.print(Panel(text, title=f"Diff: {path}", border_style="yellow", padding=(0, 1)))
    return ""  # Rendered, return empty


def _show_new_file(path: str, content: str) -> str:
    """Show a preview of a new file's content."""
    _console.print()
    lines = content.split("\n")
    preview = "\n".join(lines[:15])
    suffix = ""
    if len(lines) > 15:
        suffix = f"\n  ... ({len(lines) - 15} more lines)"
        # Detect language for syntax highlighting
    ext = Path(path).suffix.lstrip(".")
    lang_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "html": "html", "css": "css", "json": "json", "md": "markdown",
        "toml": "toml", "yaml": "yaml", "yml": "yaml",
        "sh": "bash", "bash": "bash", "sql": "sql", "rs": "rust",
        "go": "go", "java": "java", "cpp": "cpp", "c": "c",
    }
    lang = lang_map.get(ext, "text")
    _console.print(Panel(
        Syntax(preview + suffix, lang, theme="monokai", line_numbers=True),
        title=f"New: {path}",
        border_style="cyan",
        padding=(0, 1),
    ))
    return ""


def confirm_write(path: str, content: str) -> bool:
    """Show diff and ask user to confirm. Returns True if approved."""
    show_diff(path, content)
    _console.print()
    decision = input("  Write? [y]es / [n]o: ").strip().lower()
    return decision == "y"
