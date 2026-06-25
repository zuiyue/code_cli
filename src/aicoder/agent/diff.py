"""File diff preview for write_file/edit_file confirmation."""

from pathlib import Path


def show_diff(path: str, new_content: str) -> str:
    """Show a diff between existing file content and new content."""
    p = Path(path)

    if p.exists():
        old = p.read_text()
        old_lines = old.split("\n")
        new_lines = new_content.split("\n")
        lines = [f"\n  Diff: {path}"]
        shown = 0
        for i in range(max(len(old_lines), len(new_lines))):
            o = old_lines[i] if i < len(old_lines) else None
            n = new_lines[i] if i < len(new_lines) else None
            if o != n:
                if shown == 0:
                    lines.append("  --- old / +++ new")
                if o is not None:
                    lines.append(f"  - {o[:120]}")
                if n is not None:
                    lines.append(f"  + {n[:120]}")
                shown += 1
        if shown == 0:
            lines.append("  (no changes)")
        return "\n".join(lines)
    else:
        # New file preview
        content_lines = new_content.split("\n")
        preview = "\n".join(content_lines[:10])
        if len(content_lines) > 10:
            preview += "\n... (truncated)"
        return f"\n  New file: {path}\n  Preview:\n    {preview}"


def confirm_write(path: str, content: str) -> bool:
    """Show diff and ask user to confirm. Returns True if approved."""
    print(show_diff(path, content))
    decision = input("  Write? [y]es / [n]o: ").strip().lower()
    return decision == "y"
