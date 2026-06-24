from aicoder.config.loader import load_config, AppConfig


class TestLoadConfig:
    def test_loads_default_config(self, config_dir):
        cfg = load_config(config_dir)
        assert cfg.model.name == "claude-sonnet-4-5-20250929"
        assert cfg.bash.timeout_ms == 120000
        assert cfg.ui.show_thinking is True

    def test_loads_custom_config(self, config_dir):
        (config_dir / "config.toml").write_text("""
[model]
name = "custom-model"

[ui]
theme = "light"
""")
        cfg = load_config(config_dir)
        assert cfg.model.name == "custom-model"
        assert cfg.ui.theme == "light"
        assert cfg.bash.timeout_ms == 120000

    def test_missing_file_returns_defaults(self, temp_dir):
        cfg = load_config(temp_dir / ".aicoder")
        assert cfg.model.name == "claude-sonnet-4-5-20250929"
