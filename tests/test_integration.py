import subprocess
import sys


class TestIntegration:
    def test_imports_all_modules(self):
        modules = [
            "aicoder",
            "aicoder.main",
            "aicoder.config.loader",
            "aicoder.config.permissions",
            "aicoder.agent.factory",
            "aicoder.agent.prompt",
            "aicoder.agent.bash_tool",
            "aicoder.agent.subagents",
            "aicoder.cli.session",
            "aicoder.cli.permission_gate",
            "aicoder.cli.renderer",
            "aicoder.cli.repl",
            "aicoder.cli.commands",
        ]
        for mod in modules:
            __import__(mod)

    def test_main_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "aicoder.main", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--project" in result.stdout
        assert "--continue" in result.stdout

    def test_main_list_sessions_empty(self, temp_dir, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_dir))
        result = subprocess.run(
            [sys.executable, "-m", "aicoder.main", "--list-sessions"],
            capture_output=True,
            text=True,
        )
        assert "No saved sessions" in result.stdout
