import asyncio
import subprocess
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from pathlib import Path

from aicoder.cli.renderer import StreamRenderer
from aicoder.cli.commands import CommandHandler, ModelCompleter
from aicoder.cli.permission_gate import PermissionGate
from aicoder.cli.session import SessionManager
from aicoder.config.loader import AppConfig
from aicoder.config.permissions import PermissionManager
from aicoder.config.skills import SkillManager
from aicoder.agent.factory import create_agent
from aicoder.agent.bash_tool import BashSession
from aicoder.agent.models import list_models, get_model_info
from aicoder.agent.images import has_clipboard_image, read_clipboard_image
from aicoder.agent.vision import ImageAttachment
from aicoder.agent.stats import TokenTracker
from aicoder.agent.mcp_client import MCPClient
from aicoder.cli.runtime import (ensure_vision_model, resolve_image, rebuild_agent,
                                  invoke_stream)
from aicoder.util import project_hash, RECURSION_LIMIT_KEY, RECURSION_LIMIT


STYLE = Style.from_dict({
    "prompt": "#00ff00 bold",
    "toolbar": "bg:#333333 #ffffff",
})

bindings = KeyBindings()


@bindings.add("escape", "enter")
def insert_newline(event):
    """Escape+Enter inserts a newline for multi-line input."""
    event.current_buffer.insert_text("\n")


@bindings.add("c-d")
def exit_app(event):
    event.app.exit()


SCREENSHOT_TMP = "/tmp/aicoder_screenshot.png"
SCREENSHOT_FLAG = "/tmp/aicoder_screenshot.flag"


@bindings.add("f2")
def screenshot(event):
    """F2: interactive screenshot. Insert /image into buffer + set flag as backup."""
    result = subprocess.run(["screencapture", "-i", SCREENSHOT_TMP],
                             check=False, stderr=subprocess.PIPE, text=True)
    if Path(SCREENSHOT_TMP).exists() and Path(SCREENSHOT_TMP).stat().st_size > 0:
        Path(SCREENSHOT_FLAG).touch()
        # Try to insert text into the buffer for immediate visual feedback
        buf = event.app.current_buffer
        if buf is not None:
            text = f"/image {SCREENSHOT_TMP} "
            if buf.text:
                text = buf.text + " " + text
            buf.text = text
            buf.cursor_position = len(buf.text)
        event.app.invalidate()
    elif "could not create" in (result.stderr or ""):
        print("\n  Screenshot failed: macOS Screen Recording permission required.\n"
              "  Fix: System Settings > Privacy & Security > Screen Recording\n"
              "  Or use /image <path> to attach an image file.")


def run_repl(
    cfg: AppConfig,
    config_dir: Path,
    project_root: str,
    thread_id: str | None = None,
):
    ph = project_hash(project_root)
    sessions_dir = config_dir / "sessions"

    sm = SessionManager(sessions_dir)
    pm = PermissionManager(config_dir)
    gate = PermissionGate(pm, project_root)

    if thread_id is None:
        thread_id = sm.create_session(ph)

    state_db = sm.get_state_db_path(ph, thread_id)
    store_db = sm.get_store_db_path(ph, thread_id)

    def _bash_approver(command: str, cwd: str) -> bool:
        """Permission check: returns True if command is allowed."""
        if gate.is_denied(command):
            print(f"  [Denied: {command[:80]}]")
            return False
        if not gate.needs_approval(command):
            return True
        print(f"\n  Bash: {command[:150]}")
        print(f"  CWD:   {cwd}")
        decision = input("  Allow? [y]es / [n]o / [a]lways: ").strip().lower()
        if decision == "a":
            gate.allow_always(command)
            return True
        if decision == "y":
            gate.allow_session(command)
            return True
        return False

    bash_session = BashSession(project_root, cfg.ui.max_output_lines,
                               approver=_bash_approver)

    pkg_dir = Path(__file__).resolve().parent.parent
    skill_mgr = SkillManager(config_dir, pkg_dir)
    skill_paths = skill_mgr.resolve_paths(project_root)

    current_model = cfg.model.name
    agent = create_agent(cfg, project_root, bash_session, state_db,
                         store_db_path=store_db, model_name=current_model,
                         skill_paths=skill_paths)

    cmd_handler = CommandHandler(sm, str(sessions_dir), ph, thread_id)
    cmd_handler.set_model(current_model)
    cmd_handler.set_skill_manager(skill_mgr, project_root)

    token_tracker = TokenTracker()
    cmd_handler.set_token_tracker(token_tracker)
    renderer = StreamRenderer(show_thinking=cfg.ui.show_thinking, tracker=token_tracker)

    # MCP client — connect configured servers
    mcp_client = MCPClient()
    cmd_handler.set_mcp_client(mcp_client)

    # Connect to MCP servers from config
    for server_cfg in cfg.mcp.servers:
        name = server_cfg.get("name", "mcp")
        cmd = server_cfg.get("command", "")
        if cmd:
            try:
                loop.run_until_complete(mcp_client.connect_server(name, cmd))
                print(f"  MCP: {name} connected ({len(mcp_client.list_tools())} tools)")
            except Exception as e:
                print(f"  MCP: {name} failed: {e}")

    model_info = get_model_info(current_model)
    model_display = model_info["display"] if model_info else current_model
    print(f"Starting aicoder (project: {project_root}, session: {thread_id}, model: {model_display})")
    print(f"Skills loaded: {len(skill_mgr.discover(project_root))}")
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

    TOOLBAR = " [Esc+Enter] newline  [Ctrl+D] exit  [/help] commands"

    # Use a persistent event loop to avoid httpx connection issues
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    langgraph_config = {
        "configurable": {"thread_id": thread_id},
        RECURSION_LIMIT_KEY: RECURSION_LIMIT,
    }

    cmd_handler.set_export_context(agent, langgraph_config)

    while True:
        clipboard_img = None

        try:
            raw = session.prompt([("class:prompt", "> ")], bottom_toolbar=TOOLBAR)
            # prompt_toolkit overwrites the event loop; restore ours
            asyncio.set_event_loop(loop)
            if not isinstance(raw, str):
                continue
            user_input = raw.strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            # Empty input: check clipboard for image
            if has_clipboard_image():
                result = read_clipboard_image()
                if result:
                    clipboard_img = ImageAttachment(*result)
                    print(f"  Image from clipboard ({clipboard_img.size_kb}KB, {clipboard_img.mime})")
                    try:
                        user_input = session.prompt(
                            [("class:prompt", "  describe> ")],
                        ).strip()
                    except (EOFError, KeyboardInterrupt):
                        continue
                    if not user_input:
                        continue
                else:
                    print("  No image in clipboard")
                    continue
            else:
                continue

        # Handle commands
        if cmd_handler.is_command(user_input):
            result = cmd_handler.handle(user_input)
            if result == "exit":
                print("Goodbye.")
                break

            # Check for /image command
            img = resolve_image(result) if result else None
            if img:
                image_attachment, desc = img

                # Only prompt for description if user didn't provide one
                if not desc:
                    try:
                        desc = session.prompt(
                            [("class:prompt", "  describe> ")],
                        ).strip()
                    except (EOFError, KeyboardInterrupt):
                        print("  Cancelled.")
                        continue

                if not desc:
                    desc = "Analyze this image"

                try:
                    agent, current_model = ensure_vision_model(
                        agent, cfg, current_model, project_root, bash_session,
                        state_db, store_db, skill_paths,
                    )
                    cmd_handler.set_model(current_model)
                except Exception as e:
                    renderer.print_error(f"[Model switch failed: {e}]")
                    print()
                    continue

                msg = image_attachment.build_message(desc)
                try:
                    loop.run_until_complete(
                        invoke_stream(agent, None, langgraph_config,
                                                   gate, renderer, prebuilt_message=msg)
                    )
                except Exception as e:
                    renderer.print_error(f"[Error: {e}]")
                print()
                continue

            # Handle /plan with task description
            if result == "__PLAN_MODE_ON__":
                print("Plan mode — tools disabled. Use /build to enable execution.")
                task = user_input[5:].strip() if len(user_input) > 5 else ""
                if task:
                    user_input = task
                    # Fall through to regular invoke (plan prefix applied below)
                else:
                    continue

            # Handle MCP connect/disconnect
            if result and result.startswith("__MCP__CONNECT__"):
                payload = result[len("__MCP__CONNECT__"):]
                name, rest = payload.split("|", 1)
                cmd_parts = rest.split("|")
                command = cmd_parts[0]
                args = cmd_parts[1].split() if len(cmd_parts) > 1 and cmd_parts[1] else []
                try:
                    tools = loop.run_until_complete(mcp_client.connect_server(name, command, args))
                    extra_mcp_tools = mcp_client.build_langchain_tools()
                    agent = rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                                           current_model, skill_paths, extra_tools=extra_mcp_tools)
                    print(f"  MCP connected: {name} ({len(tools)} tools)")
                    for t in tools:
                        print(f"    - {t.name}")
                except Exception as e:
                    print(f"  MCP connect failed: {e}")
                continue

            if result and result.startswith("__MCP__DISCONNECT__"):
                name = result[len("__MCP__DISCONNECT__"):]
                try:
                    loop.run_until_complete(mcp_client.disconnect_server(name))
                    extra_mcp_tools = mcp_client.build_langchain_tools()
                    agent = rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                                           current_model, skill_paths, extra_tools=extra_mcp_tools)
                    print(f"  MCP disconnected: {name}")
                except Exception as e:
                    print(f"  MCP disconnect failed: {e}")
                continue

            # Existing command handling
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
                agent = rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                                       current_model, skill_paths)
                completer.set_skill_names([s.name for s in skill_mgr.discover(project_root)])

            if isinstance(result, str) and result.startswith("\n  Current:"):
                print(result)
                try:
                    choice = session.prompt(
                        [("class:prompt", "  model> ")],
                        completer=ModelCompleter(),
                    ).strip()
                    if choice:
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
                            agent = rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                                                   current_model, skill_paths)
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

        # Regular text message (with optional image from clipboard detection)
        if cmd_handler.current_model != current_model:
            current_model = cmd_handler.current_model
            agent = rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                                   current_model, skill_paths)

        try:
            if clipboard_img is not None:
                agent, current_model = ensure_vision_model(
                    agent, cfg, current_model, project_root, bash_session,
                    state_db, store_db, skill_paths,
                )
                cmd_handler.set_model(current_model)
                msg = clipboard_img.build_message(user_input)
                loop.run_until_complete(
                    invoke_stream(agent, None, langgraph_config,
                                               gate, renderer, prebuilt_message=msg)
                )
            else:
                if cmd_handler.plan_mode:
                    user_input = (
                        "You are in PLAN MODE. Your role is to be an interactive product architect.\n\n"
                        "WORKFLOW:\n"
                        "1. Understand the goal — ask ONE clarifying question at a time\n"
                        "2. Propose 2-3 approaches with trade-offs\n"
                        "3. Write a design document to docs/specs/<topic>.md\n"
                        "4. Ask user to review before proceeding\n\n"
                        "RULES:\n"
                        "- Ask only ONE question per response\n"
                        "- Never execute — tools are disabled\n"
                        "- Write specs to docs/specs/YYYY-MM-DD-topic.md\n"
                        "- After writing spec, say: 'Spec saved to docs/specs/. Review and /build to implement.'\n\n"
                        "TASK:\n" + user_input
                    )
                loop.run_until_complete(
                    invoke_stream(agent, user_input, langgraph_config, gate, renderer,
                                  plan_mode=cmd_handler.plan_mode)
                )
        except Exception as e:
            renderer.print_error(f"[Error: {e}]")
        print()

