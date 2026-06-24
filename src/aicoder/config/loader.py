from dataclasses import dataclass, field
from pathlib import Path
import tomllib


@dataclass
class ModelConfig:
    provider: str = "deepseek"
    name: str = "deepseek-chat"
    api_key: str = ""
    api_base: str = "https://api.deepseek.com"
    temperature: float = 0.0


@dataclass
class BashConfig:
    timeout_ms: int = 120000
    allowed_commands: list[str] = field(default_factory=list)


@dataclass
class UIConfig:
    theme: str = "dark"
    show_thinking: bool = True
    max_output_lines: int = 500


@dataclass
class PromptConfig:
    extra_rules: str = ""


@dataclass
class ProjectConfig:
    root: str = "."
    auto_load_agents_md: bool = True


@dataclass
class AppConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    bash: BashConfig = field(default_factory=BashConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    prompt: PromptConfig = field(default_factory=PromptConfig)
    project: ProjectConfig = field(default_factory=ProjectConfig)


def _apply_overrides(cfg: AppConfig, raw: dict) -> AppConfig:
    if "model" in raw:
        for k, v in raw["model"].items():
            setattr(cfg.model, k, v)
    if "bash" in raw:
        for k, v in raw["bash"].items():
            setattr(cfg.bash, k, v)
    if "ui" in raw:
        for k, v in raw["ui"].items():
            setattr(cfg.ui, k, v)
    if "prompt" in raw:
        for k, v in raw["prompt"].items():
            setattr(cfg.prompt, k, v)
    if "project" in raw:
        for k, v in raw["project"].items():
            setattr(cfg.project, k, v)
    return cfg


def load_config(config_dir: Path) -> AppConfig:
    cfg = AppConfig()
    config_path = config_dir / "config.toml"
    if config_path.exists():
        raw = tomllib.loads(config_path.read_text())
        cfg = _apply_overrides(cfg, raw)
    return cfg
