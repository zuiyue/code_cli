"""File diff preview — opencode-style side-by-side comparison."""

from pathlib import Path
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.columns import Columns as RichColumns

_console = Console()


def show_diff(path: str, new_content: str, max_lines: int = 40) -> str:
    """Side-by-side diff for existing files, syntax preview for new files."""
    p = Path(path)

    if not p.exists():
        return _new_file_preview(path, new_content)

    old_lines = p.read_text().split("\n")
    new_lines = new_content.split("\n")
    return _side_by_side(path, old_lines, new_lines, max_lines)


def _side_by_side(path: str, old: list[str], new: list[str], max_lines: int) -> str:
    """Render side-by-side diff using rich Columns."""
    max_len = max(len(old), len(new))
    display_old = old[:max_lines]
    display_new = new[:max_lines]
    truncated = max_len > max_lines

    left = Text()
    right = Text()

    i = 0
    while i < max(len(display_old), len(display_new)):
        o = display_old[i] if i < len(display_old) else None
        n = display_new[i] if i < len(display_new) else None

        # Line number
        lnum = Text(f"{i+1:4d} ", style="dim")

        if o is not None:
            left.append(lnum)
            if n != o and n is not None:
                left.append(o[:120], style="bold red")
                left.append("\n")
                right.append(lnum)
                right.append(n[:120], style="bold green")
                right.append("\n")
                # Also show deleted lines that have no match
                # Check if old has lines that new doesn't
            elif n is None:
                left.append(o[:120], style="bold red")
                left.append("\n")
                right.append(lnum)
                right.append("", style="dim")
                right.append("\n")
            elif o == n:
                left.append(o[:120], style="dim")
                left.append("\n")
                right.append(lnum)
                right.append(n[:120], style="dim")
                right.append("\n")
        elif n is not None:
            left.append(lnum)
            left.append("", style="dim")
            left.append("\n")
            right.append(lnum)
            right.append(n[:120], style="bold green")
            right.append("\n")
        i += 1

    left_panel = Panel(left, title="[red]Original[/red]", border_style="red", padding=(0, 1))
    right_panel = Panel(right, title="[green]Modified[/green]", border_style="green", padding=(0, 1))

    _console.print()
    _console.print(RichColumns([left_panel, right_panel], equal=True, expand=True))
    if truncated:
        _console.print(f"  [dim]... ({max_len - max_lines} more lines)[/dim]")
    return ""


def _new_file_preview(path: str, content: str) -> str:
    """Syntax-highlighted preview for new files."""
    _console.print()
    lines = content.split("\n")
    preview = "\n".join(lines[:20])
    suffix = ""
    if len(lines) > 20:
        suffix = f"\n... ({len(lines) - 20} more lines)"

    ext = Path(path).suffix.lstrip(".")
    lang = _detect_lang(ext)
    _console.print(Panel(
        Syntax(preview + suffix, lang, theme="monokai", line_numbers=True),
        title=f"New: {path}",
        border_style="cyan",
        padding=(0, 1),
    ))
    return ""


def _detect_lang(ext: str) -> str:
    return {
        "py": "python", "js": "javascript", "ts": "typescript",
        "tsx": "tsx", "jsx": "jsx",
        "html": "html", "css": "css", "json": "json", "md": "markdown",
        "toml": "toml", "yaml": "yaml", "yml": "yaml",
        "sh": "bash", "bash": "bash", "sql": "sql", "rs": "rust",
        "go": "go", "java": "java", "cpp": "cpp", "c": "c", "h": "c",
        "rb": "ruby", "php": "php", "swift": "swift", "kt": "kotlin",
    }.get(ext, "text")


def confirm_write(path: str, content: str) -> bool:
    show_diff(path, content)
    _console.print()
    decision = input("  Write? [y]es / [n]o: ").strip().lower()
    return decision == "y"
