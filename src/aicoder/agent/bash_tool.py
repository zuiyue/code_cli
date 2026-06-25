import os
import subprocess
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
        if not command or not command.strip():
            return "(no command)"

        timeout_sec = timeout / 1000.0

        # Fold cwd tracking into a single execution to avoid double side-effects
        wrapped = f"cd {self._cwd} && {{ {command}; }}; echo __CWD__:$PWD"
        try:
            result = subprocess.run(
                ["/bin/bash", "-c", wrapped],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=str(self._cwd),
                env={**os.environ, "HOME": os.environ.get("HOME", "/tmp")},
            )
        except subprocess.TimeoutExpired:
            return f"[Command timed out after {timeout_sec}s]"

        output = result.stdout or ""
        stderr = result.stderr or ""

        # Split __CWD__ marker to extract cwd
        if "__CWD__:" in output:
            idx = output.rindex("__CWD__:")
            cwd_line = output[idx + len("__CWD__:"):]
            new_cwd = cwd_line.split("\n")[0].strip()
            output = output[:idx]
            if new_cwd and new_cwd.startswith(str(self._root)):
                self._cwd = Path(new_cwd)

        if stderr:
            output = (output.rstrip() + "\n" + stderr.rstrip()).strip()

        # Truncate output
        lines = output.split("\n")
        if len(lines) > self.max_output_lines:
            output = "\n".join(lines[:self.max_output_lines])
            output += f"\n[Output truncated: {len(lines)} lines total, showing first {self.max_output_lines}]"

        output = output.strip()
        return output if output else "(no output)"


def create_bash_tool(session: BashSession):
    """Create a bash tool bound to a specific BashSession instance."""
    @tool
    def bash(command: str, timeout: int = 120000) -> str:
        """Execute a bash command in the project directory. Returns stdout+stderr."""
        return session.run(command, timeout=timeout)

    return bash
