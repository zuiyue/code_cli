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

    print(f"Starting aicoder (project: {project_root}, session: {thread_id})")
    print("Type /help for commands.\n")
    agent = create_agent(cfg, project_root, state_db)

    cmd_handler = CommandHandler(sm, str(sessions_dir), ph, thread_id)
    renderer = StreamRenderer()

    history_path = config_dir / "history" / f"{ph}.txt"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    session = PromptSession(
        history=FileHistory(str(history_path)),
        key_bindings=bindings,
        style=STYLE,
        multiline=False,
        wrap_lines=True,
    )

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
            print(result)
            continue

        config = {"configurable": {"thread_id": thread_id}}
        try:
            events = agent.astream_events(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
                version="v2",
            )
            final_text = renderer.render(events, show_thinking=cfg.ui.show_thinking)
            if final_text:
                print(f"\n{final_text}")
        except Exception as e:
            error_msg = str(e)
            if "interrupt" in error_msg.lower():
                _handle_interrupt(error_msg, agent, config, gate, renderer, cfg)
            else:
                print(f"\n[Error: {error_msg}]")
        print()


def _handle_interrupt(error_msg, agent, config, gate, renderer, cfg):
    print(f"\n[Interrupt: bash command needs approval]")
    state = agent.get_state(config)
    interrupts = []
    if state and hasattr(state, "tasks") and state.tasks:
        for task in state.tasks:
            if hasattr(task, "interrupts"):
                interrupts.extend(task.interrupts)

    from langgraph.types import Command

    for interrupt in interrupts:
        tool_input = {}
        if hasattr(interrupt, "value") and isinstance(interrupt.value, dict):
            tool_input = interrupt.value.get("input", {})
        command = tool_input.get("command", str(tool_input))

        if gate.is_denied(command):
            agent.invoke(Command(resume={"decision": "deny"}), config)
            print(f"[Denied: {command[:80]}]")
            continue

        if not gate.needs_approval(command):
            agent.invoke(Command(resume={"decision": "allow"}), config)
            continue

        print(f"\n  Bash command: {command[:200]}")
        decision = input("  Allow? [y]es / [n]o / [a]lways: ").strip().lower()

        if decision == "a":
            gate.allow_always(command)
            agent.invoke(Command(resume={"decision": "allow"}), config)
        elif decision == "y":
            gate.allow_session(command)
            agent.invoke(Command(resume={"decision": "allow"}), config)
        else:
            agent.invoke(Command(resume={"decision": "deny"}), config)
