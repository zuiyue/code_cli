import argparse
import os
from pathlib import Path

from aicoder.config.loader import load_config
from aicoder.agent.models import list_models


def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / "aicoder"


def _project_hash(project_root: str) -> str:
    import hashlib
    return hashlib.sha256(str(Path(project_root).resolve()).encode()).hexdigest()[:12]


def main():
    parser = argparse.ArgumentParser(
        description="AI-powered terminal coding assistant"
    )
    parser.add_argument(
        "--project", "-p",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--model", "-m",
        default="deepseek-chat",
        choices=list_models(),
        help="Model to use (default: deepseek-chat)",
    )
    parser.add_argument(
        "--continue", "-c",
        dest="continue_session",
        action="store_true",
        help="Continue last session for this project",
    )
    parser.add_argument(
        "--list-sessions", "-l",
        action="store_true",
        help="List saved sessions and exit",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit",
    )
    args = parser.parse_args()

    if args.list_models:
        from aicoder.agent.models import get_model_info
        for name in list_models():
            info = get_model_info(name)
            print(f"  {name:25s} {info['display']} ({info['provider']})")
        return

    project_root = str(Path(args.project).resolve())
    config_dir = get_config_dir()
    cfg = load_config(config_dir)

    if not cfg.model.api_key:
        cfg.model.api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    # CLI --model overrides config
    cfg.model.name = args.model

    ph = _project_hash(project_root)

    if args.list_sessions:
        from aicoder.cli.session import SessionManager
        sm = SessionManager(config_dir / "sessions")
        sessions = sm.list_sessions(ph)
        if not sessions:
            print("No saved sessions.")
        else:
            print(f"Sessions for {project_root}:")
            for s in sessions:
                print(f"  {s['thread_id']}")
        return

    thread_id = None
    if args.continue_session:
        from aicoder.cli.session import SessionManager
        sm = SessionManager(config_dir / "sessions")
        sessions = sm.list_sessions(ph)
        if sessions:
            thread_id = sessions[0]["thread_id"]
            print(f"Continuing session: {thread_id}")

    from aicoder.cli.repl import run_repl
    run_repl(cfg, config_dir, project_root, thread_id)


if __name__ == "__main__":
    main()
