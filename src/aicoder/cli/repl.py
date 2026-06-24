import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from pathlib import Path

from aicoder.cli.renderer import StreamRenderer
from aicoder.cli.commands import CommandHandler
from aicoder.cli.permission_gate import PermissionGate
from aicoder.cli.session import SessionManager
from aicoder.config.loader import AppConfig
from aicoder.config.permissions import PermissionManager
from aicoder.agent.factory import create_agent
from aicoder.agent.bash_tool import init_bash_session
from aicoder.agent.models import list_models, get_model_info
from aicoder.cli.commands import ModelCompleter
from aicoder.config.skills import SkillManager


STYLE = Style.from_dict({
    "prompt": "#00ff00 bold",
    "toolbar": "bg:#333333 #ffffff",
})

bindings = KeyBindings()


@bindings.add("c-d")
def exit_app(event):
    event.app.exit()


def _project_hash(project_root: str) -> str:
    import hashlib
    return hashlib.sha256(str(Path(project_root).resolve()).encode()).hexdigest()[:12]


def _rebuild_agent(cfg, project_root, state_db, model_name, skill_paths=None):
    """Recreate agent with a different model and/or skills."""
    return create_agent(cfg, project_root, state_db, model_name=model_name, skill_paths=skill_paths)


def run_repl(
    cfg: AppConfig,
    config_dir: Path,
    project_root: str,
    thread_id: str | None = None,
):
    ph = _project_hash(project_root)
    sessions_dir = config_dir / "sessions"

    sm = SessionManager(sessions_dir)
    pm = PermissionManager(config_dir)
    gate = PermissionGate(pm, project_root)

    if thread_id is None:
        thread_id = sm.create_session(ph)

    state_db = sm.get_state_db_path(ph, thread_id)

    init_bash_session(project_root, cfg.ui.max_output_lines)

    # Skills
    pkg_dir = Path(__file__).resolve().parent.parent
    skill_mgr = SkillManager(config_dir, pkg_dir)
    skill_paths = skill_mgr.resolve_paths(project_root)

    current_model = cfg.model.name
    agent = create_agent(cfg, project_root, state_db,
                         model_name=current_model, skill_paths=skill_paths)

    cmd_handler = CommandHandler(sm, str(sessions_dir), ph, thread_id)
    cmd_handler.set_model(current_model)
    cmd_handler.set_skill_manager(skill_mgr, project_root)
    renderer = StreamRenderer(show_thinking=cfg.ui.show_thinking)

    model_info = get_model_info(current_model)
    model_display = model_info["display"] if model_info else current_model
    print(f"Starting aicoder (project: {project_root}, session: {thread_id}, model: {model_display})")
    skill_count = len(skill_mgr.discover(project_root))
    print(f"Skills loaded: {skill_count}")
    print("Type /help for commands.\n")

    history_path = config_dir / "history" / f"{ph}.txt"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    completer = ModelCompleter()
    completer.set_skill_names([s.name for s in skill_mgr.discover(project_root)])
    session = PromptSession(
        history=FileHistory(str(history_path)),
        key_bindings=bindings,
        style=STYLE,
        multiline=False,
        wrap_lines=True,
        completer=completer,
    )

    langgraph_config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}

    while True:
        try:
            user_input = session.prompt([("class:prompt", "> ")]).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if cmd_handler.is_command(user_input):
            result = cmd_handler.handle(user_input)
            if result == "exit":
                print("Goodbye.")
                break

            # Check if model changed
            new_model = cmd_handler.current_model
            skills_changed = "/skill install" in user_input or "/skill remove" in user_input

            if new_model != current_model or skills_changed:
                if new_model != current_model:
                    old_info = get_model_info(current_model)
                    new_info = get_model_info(new_model)
                    old_name = old_info["display"] if old_info else current_model
                    new_name = new_info["display"] if new_info else new_model
                    current_model = new_model
                    print(f"  {old_name} -> {new_name}")
                skill_paths = skill_mgr.resolve_paths(project_root)
                agent = _rebuild_agent(cfg, project_root, state_db, current_model, skill_paths)
                completer.set_skill_names([s.name for s in skill_mgr.discover(project_root)])

            # Handle /model without args: enter interactive selection
            if result and result.startswith("\n  Current:"):
                print(result)
                try:
                    choice = session.prompt(
                        [("class:prompt", "  model> ")],
                        completer=ModelCompleter(),
                    ).strip()
                    if choice:
                        # Try number first
                        models = list_models()
                        if choice.isdigit() and 1 <= int(choice) <= len(models):
                            choice = models[int(choice) - 1]
                        if choice in models:
                            old_info = get_model_info(current_model)
                            new_info = get_model_info(choice)
                            old_name = old_info["display"] if old_info else current_model
                            new_name = new_info["display"] if new_info else choice
                            cmd_handler.set_model(choice)
                            current_model = choice
                            agent = _rebuild_agent(cfg, project_root, state_db, current_model)
                            print(f"  Switched: {old_name} -> {new_name}")
                        else:
                            print(f"  Unknown model: {choice}")
                    else:
                        print("  Canceled.")
                except (EOFError, KeyboardInterrupt):
                    print("  Canceled.")
            else:
                print(result)
            continue

        # Check model sync
        if cmd_handler.current_model != current_model:
            current_model = cmd_handler.current_model
            skill_paths = skill_mgr.resolve_paths(project_root)
            agent = _rebuild_agent(cfg, project_root, state_db, current_model, skill_paths)

        # Run the async invoke loop
        try:
            asyncio.run(
                _async_invoke_with_stream(agent, user_input, langgraph_config, gate, renderer)
            )
        except Exception as e:
            renderer.print_error(f"[Error: {e}]")
        print()


async def _async_invoke_with_stream(agent, user_input, config, gate, renderer, max_retries=5):
    """Invoke agent with streaming; handle interrupt + approval."""
    from langgraph.types import Command

    next_input = {"messages": [{"role": "user", "content": user_input}]}

    for retry in range(max_retries):
        try:
            events = agent.astream_events(next_input, config=config, version="v2")
            final = await renderer.render_stream(events)
            if final:
                renderer.print_response(final)
            return
        except Exception as e:
            error_msg = str(e)
            if "interrupt" not in error_msg.lower():
                if "LangGraphInterrupt" in type(e).__name__:
                    pass  # handle below
                else:
                    renderer.print_error(f"[Error: {error_msg}]")
                    return

        # Handle interrupt
        state = agent.get_state(config)
        interrupts = []
        if state and hasattr(state, "tasks") and state.tasks:
            for task in state.tasks:
                if hasattr(task, "interrupts"):
                    interrupts.extend(task.interrupts)

        if not interrupts:
            # Try LangGraphInterrupt
            if hasattr(e, "__cause__"):
                renderer.print_error(f"[Interrupt: {error_msg[:100]}]")
            return

        for interrupt in interrupts:
            tool_input = {}
            if hasattr(interrupt, "value") and isinstance(interrupt.value, dict):
                tool_input = interrupt.value.get("input", {})
            command = tool_input.get("command", str(tool_input))

            if gate.is_denied(command):
                renderer.print_info(f"  [Denied: {command[:80]}]")
                next_input = Command(resume={"decision": "deny"})
                continue

            if not gate.needs_approval(command):
                next_input = Command(resume={"decision": "allow"})
                continue

            print(f"\n  Bash command: {command[:200]}")
            decision = input("  Allow? [y]es / [n]o / [a]lways: ").strip().lower()

            if decision == "a":
                gate.allow_always(command)
                next_input = Command(resume={"decision": "allow"})
            elif decision == "y":
                gate.allow_session(command)
                next_input = Command(resume={"decision": "allow"})
            else:
                next_input = Command(resume={"decision": "deny"})

    renderer.print_error("[Max retries exceeded]")
