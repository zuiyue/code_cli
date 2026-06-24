import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def config_dir(temp_dir):
    cfg = temp_dir / ".aicoder"
    cfg.mkdir()
    (cfg / "config.toml").write_text("""
[model]
provider = "deepseek"
name = "deepseek-chat"
api_key = "test-key"
api_base = "https://api.deepseek.com"

[bash]
timeout_ms = 120000
allowed_commands = []
interrupt = true

[ui]
theme = "dark"
show_thinking = true
max_output_lines = 500

[prompt]
extra_rules = ""

[project]
root = "."
auto_load_agents_md = true
""")
    return cfg


@pytest.fixture
def project_dir(temp_dir):
    proj = temp_dir / "myproject"
    proj.mkdir()
    (proj / "AGENTS.md").write_text("# Project Rules\nUse pytest for testing.")
    return proj


class FakeSessionManager:
    """Shared fake for command handler tests."""
    def __init__(self):
        self.deleted = []
        self.sessions_data = []

    def list_sessions(self, ph):
        return self.sessions_data

    def delete_session(self, ph, tid):
        self.deleted.append(tid)
