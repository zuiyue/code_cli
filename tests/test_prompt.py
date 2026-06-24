from aicoder.agent.prompt import build_system_prompt
from aicoder.config.loader import AppConfig


class TestBuildSystemPrompt:
    def test_base_prompt_always_included(self, config_dir):
        cfg = AppConfig()
        prompt = build_system_prompt(cfg, project_root="/fake")
        assert "software engineering" in prompt.lower()

    def test_includes_agents_md_when_present(self, config_dir, project_dir):
        cfg = AppConfig()
        prompt = build_system_prompt(cfg, project_root=str(project_dir))
        assert "pytest for testing" in prompt

    def test_no_agents_md_does_not_error(self, config_dir, temp_dir):
        cfg = AppConfig()
        prompt = build_system_prompt(cfg, project_root=str(temp_dir))
        assert len(prompt) > 0

    def test_includes_user_extra_rules(self, config_dir):
        cfg = AppConfig()
        cfg.prompt.extra_rules = "Always use snake_case."
        prompt = build_system_prompt(cfg, project_root="/fake")
        assert "Always use snake_case" in prompt

    def test_prompt_order_base_first_extras_last(self, config_dir):
        cfg = AppConfig()
        cfg.prompt.extra_rules = "ZZZ_EXTRA_RULE"
        prompt = build_system_prompt(cfg, project_root="/fake")
        base_pos = prompt.lower().index("software engineering")
        extra_pos = prompt.index("ZZZ_EXTRA_RULE")
        assert base_pos < extra_pos
