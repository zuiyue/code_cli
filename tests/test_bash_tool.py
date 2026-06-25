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
        assert "truncated" in result.lower()

    def test_empty_command(self, temp_dir):
        session = BashSession(str(temp_dir))
        result = session.run("", timeout=5000)
        assert "no command" in result.lower()


class TestBashTool:
    def test_creates_functional_tool(self, temp_dir):
        session = BashSession(str(temp_dir))
        tool = create_bash_tool(session)
        result = tool.invoke({"command": "echo tooltest"})
        assert "tooltest" in result

    def test_session_passed_explicitly(self, temp_dir):
        s1 = BashSession(str(temp_dir))
        s2 = BashSession(str(temp_dir))
        t1 = create_bash_tool(s1)
        t2 = create_bash_tool(s2)
        s1.run(f"mkdir -p {temp_dir}/a && cd {temp_dir}/a")
        r1 = t1.invoke({"command": "pwd"})
        r2 = t2.invoke({"command": "pwd"})
        assert str(temp_dir / "a") in r1
        assert str(temp_dir / "a") not in r2
