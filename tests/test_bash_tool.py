import pytest
from pathlib import Path
from aicoder.agent.bash_tool import BashSession, create_bash_tool


class TestBashSession:
    def test_executes_basic_command(self, temp_dir):
        session = BashSession(str(temp_dir))
        result = session.run("echo hello")
        assert "hello" in result

    def test_cd_changes_directory(self, temp_dir):
        sub = temp_dir / "subdir"
        sub.mkdir()
        session = BashSession(str(temp_dir))
        session.run(f"cd {sub}")
        result = session.run("pwd")
        assert sub.resolve() == Path(result.strip()).resolve()

    def test_timeout_kills_process(self, temp_dir):
        session = BashSession(str(temp_dir))
        result = session.run("sleep 10", timeout=500)
        assert "timed out" in result.lower()

    def test_returns_stderr(self, temp_dir):
        session = BashSession(str(temp_dir))
        result = session.run("echo err >&2", timeout=5000)
        assert "err" in result

    def test_output_truncation(self, temp_dir):
        session = BashSession(str(temp_dir))
        session.max_output_lines = 5
        result = session.run("for i in $(seq 1 20); do echo line $i; done")
        lines = result.strip().split("\n")
        assert len(lines) <= 7
        assert "truncated" in result.lower()


class TestBashTool:
    def test_creates_functional_tool(self, temp_dir):
        tool = create_bash_tool(str(temp_dir))
        result = tool.invoke({"command": "echo tooltest"})
        assert "tooltest" in result
