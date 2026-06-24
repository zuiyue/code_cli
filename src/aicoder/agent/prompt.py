from pathlib import Path
from aicoder.config.loader import AppConfig

BASE_SYSTEM_PROMPT = """You are an AI coding assistant. You help with software engineering tasks.
You can read and write files, execute bash commands, search codebases, and delegate tasks.

Guidelines:
- Be concise and direct in your responses.
- Use available tools to complete tasks effectively.
- When running commands, explain what they do.
- Follow the conventions and patterns in the codebase you're working with.
- Write clean, idiomatic code.
"""


def build_system_prompt(cfg: AppConfig, project_root: str) -> str:
    parts = [BASE_SYSTEM_PROMPT]

    if cfg.project.auto_load_agents_md:
        agents_md = Path(project_root) / "AGENTS.md"
        if agents_md.exists():
            content = agents_md.read_text().strip()
            if content:
                parts.append(f"\n--- Project Instructions (AGENTS.md) ---\n{content}")

    if cfg.prompt.extra_rules.strip():
        parts.append(f"\n--- User Rules ---\n{cfg.prompt.extra_rules.strip()}")

    return "\n\n".join(parts)
