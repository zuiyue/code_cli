from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Any


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
    interrupt: bool = True


@dataclass
class UIConfig:
    theme: str = "dark"
    show_thinking: bool = True
    max_output_lines: int = 500


@dataclass
class PromptConfig:
    extra_rules: str = ""


@dataclass
class MCPConfig:
    servers: list[dict] = field(default_factory=list)


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
    mcp: MCPConfig = field(default_factory=MCPConfig)
    project: ProjectConfig = field(default_factory=ProjectConfig)


_KNOWN_SECTIONS = {"model": ModelConfig, "bash": BashConfig, "ui": UIConfig,
                   "prompt": PromptConfig, "project": ProjectConfig}


def _apply_overrides(cfg: AppConfig, raw: dict[str, Any]) -> AppConfig:
    for section_name, section_data in raw.items():
        target = getattr(cfg, section_name, None)
        if target is None:
            continue
        for k, v in section_data.items():
            if hasattr(target, k):
                setattr(target, k, v)
    return cfg


def load_config(config_dir: Path) -> AppConfig:
    cfg = AppConfig()
    config_path = config_dir / "config.toml"
    if config_path.exists():
        try:
            raw = tomllib.loads(config_path.read_text())
            cfg = _apply_overrides(cfg, raw)
        except (tomllib.TOMLDecodeError, OSError) as e:
            import sys
            print(f"Warning: failed to parse {config_path}: {e}", file=sys.stderr)
            print("Using default configuration.", file=sys.stderr)
    return cfg
