import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def temp_dir():
    """Temporary directory that cleans up after test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def config_dir(temp_dir):
    """Simulated ~/.aicoder config directory with default config.toml."""
    cfg = temp_dir / ".aicoder"
    cfg.mkdir()
    config_toml = cfg / "config.toml"
    config_toml.write_text("""
[model]
provider = "anthropic"
name = "claude-sonnet-4-5-20250929"

[bash]
timeout_ms = 120000
allowed_commands = []

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
    """Simulated project directory with AGENTS.md."""
    proj = temp_dir / "myproject"
    proj.mkdir()
    (proj / "AGENTS.md").write_text("# Project Rules\nUse pytest for testing.")
    return proj
