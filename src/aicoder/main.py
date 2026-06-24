import argparse
import os
from pathlib import Path

from aicoder.config.loader import load_config
from aicoder.agent.models import list_models, get_model_info
from aicoder.util import project_hash


def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / "aicoder"


def main():
    models = list_models()
    parser = argparse.ArgumentParser(description="AI-powered terminal coding assistant")
    parser.add_argument("--project", "-p", default=".", help="Project root directory")
    parser.add_argument("--model", "-m", default="deepseek-chat", choices=models, help="Model to use")
    parser.add_argument("--continue", "-c", dest="continue_session", action="store_true",
                        help="Continue last session")
    parser.add_argument("--list-sessions", "-l", action="store_true", help="List sessions and exit")
    parser.add_argument("--list-models", action="store_true", help="List models and exit")
    args = parser.parse_args()

    if args.list_models:
        for name in models:
            info = get_model_info(name)
            print(f"  {name:25s} {info['display']} ({info['provider']})")
        return

    project_root_str = str(Path(args.project).resolve())
    config_dir = get_config_dir()
    cfg = load_config(config_dir)

    # Resolve API key: config value > model's env var > default empty
    if not cfg.model.api_key:
        info = get_model_info(args.model) or {}
        env_key = info.get("env_key", "DEEPSEEK_API_KEY")
        cfg.model.api_key = os.environ.get(env_key, "")
    cfg.model.name = args.model

    ph = project_hash(project_root_str)

    if args.list_sessions:
        from aicoder.cli.session import SessionManager
        sm = SessionManager(config_dir / "sessions")
        sessions = sm.list_sessions(ph)
        if not sessions:
            print("No saved sessions.")
        else:
            print(f"Sessions for {project_root_str}:")
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
    run_repl(cfg, config_dir, project_root_str, thread_id)


if __name__ == "__main__":
    main()
