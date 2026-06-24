import os
import subprocess
import shlex
from pathlib import Path
from langchain.tools import tool


class BashSession:
    def __init__(self, root: str, max_output_lines: int = 500):
        self._root = Path(root).absolute()
        self._cwd = self._root
        self.max_output_lines = max_output_lines

    @property
    def cwd(self) -> str:
        return str(self._cwd)

    def run(self, command: str, timeout: int = 120000) -> str:
        timeout_sec = timeout / 1000.0
        try:
            result = subprocess.run(
                ["/bin/bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=str(self._cwd),
                env={**os.environ, "HOME": os.environ.get("HOME", "/tmp")},
            )
        except subprocess.TimeoutExpired:
            return f"[Command timed out after {timeout_sec}s]"

        output = result.stdout
        if result.stderr:
            output += result.stderr

        # Track cwd changes: run the command prefixed with cd to current dir
        track_cwd = f"cd {shlex.quote(str(self._cwd))} && {command} && pwd"
        try:
            cwd_result = subprocess.run(
                ["/bin/bash", "-c", track_cwd],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self._cwd),
            )
            new_cwd = cwd_result.stdout.strip()
            if new_cwd and new_cwd.startswith(str(self._root)):
                self._cwd = Path(new_cwd)
        except Exception:
            pass

        # Truncate output
        lines = output.split("\n")
        if len(lines) > self.max_output_lines:
            output = "\n".join(lines[:self.max_output_lines])
            output += f"\n[Output truncated: {len(lines)} lines total, showing first {self.max_output_lines}]"

        output = output.strip()
        return output if output else "(no output)"


_session: BashSession | None = None


def init_bash_session(root: str, max_output_lines: int = 500):
    global _session
    _session = BashSession(root, max_output_lines)


def create_bash_tool(project_root: str):
    global _session
    if _session is None:
        _session = BashSession(project_root)

    @tool
    def bash(command: str, timeout: int = 120000) -> str:
        """Execute a bash command in the project directory. Returns stdout+stderr."""
        global _session
        return _session.run(command, timeout=timeout)

    return bash
