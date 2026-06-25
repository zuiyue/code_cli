import asyncio
import os
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
from aicoder.agent.models import list_models, get_model_info, supports_vision
from aicoder.agent.images import read_image as _read_image_raw, has_clipboard_image, read_clipboard_image, ImageError
from aicoder.agent.vision import ImageAttachment, pick_vision_model, describe_model
from aicoder.agent.stats import TokenTracker
from aicoder.agent.mcp_client import MCPClient
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




def _ensure_vision_model(agent, cfg, current_model, project_root, bash_session,
                          state_db, store_db, skill_paths):
    """Auto-switch to vision model if needed."""
    if supports_vision(current_model):
        return agent, current_model

    chosen = pick_vision_model()
    if not chosen:
        raise RuntimeError(
            "No vision model with API key found.\n"
            "  Set ZHIPUAI_API_KEY for GLM-4V or OPENAI_API_KEY for GPT-4o."
        )

    old_display = describe_model(current_model)
    new_display = describe_model(chosen)
    print(f"  Auto-switch: {old_display} -> {new_display} (image support)")

    new_agent = _rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                                chosen, skill_paths)
    return new_agent, chosen


def _resolve_image(cmd_result) -> tuple[ImageAttachment, str] | None:
    """Parse image command result. Returns (ImageAttachment, description) or None."""
    if not isinstance(cmd_result, str):
        return None
    if cmd_result.startswith("__IMAGE_FILE__"):
        payload = cmd_result[len("__IMAGE_FILE__"):]
        if "|" in payload:
            path, desc = payload.split("|", 1)
        else:
            path, desc = payload, ""
        try:
            img = ImageAttachment(*_read_image_raw(path), source=path)
        except ImageError as e:
            print(f"  {e}")
            return None
        print(f"  Image: {path} ({img.size_kb}KB, {img.mime})")
        return (img, desc)
    elif cmd_result == "__IMAGE_CLIPBOARD__":
        result = read_clipboard_image()
        if result:
            b64, mime = result
            img = ImageAttachment(b64, mime, source="clipboard")
            print(f"  Image from clipboard ({img.size_kb}KB, {img.mime})")
            return (img, "")
    return None

def _rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                   model_name, skill_paths=None, extra_tools=None):
    return create_agent(cfg, project_root, bash_session, state_db,
                        store_db_path=store_db, model_name=model_name,
                        skill_paths=skill_paths, extra_tools=extra_tools)


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
            img = _resolve_image(result) if result else None
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
                    agent, current_model = _ensure_vision_model(
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
                        _async_invoke_with_stream(agent, None, langgraph_config,
                                                   gate, renderer, prebuilt_message=msg)
                    )
                except Exception as e:
                    renderer.print_error(f"[Error: {e}]")
                print()
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
                    agent = _rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
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
                    agent = _rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
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
                agent = _rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
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
                            agent = _rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
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
            agent = _rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                                   current_model, skill_paths)

        try:
            if clipboard_img is not None:
                agent, current_model = _ensure_vision_model(
                    agent, cfg, current_model, project_root, bash_session,
                    state_db, store_db, skill_paths,
                )
                cmd_handler.set_model(current_model)
                msg = clipboard_img.build_message(user_input)
                loop.run_until_complete(
                    _async_invoke_with_stream(agent, None, langgraph_config,
                                               gate, renderer, prebuilt_message=msg)
                )
            else:
                loop.run_until_complete(
                    _async_invoke_with_stream(agent, user_input, langgraph_config, gate, renderer)
                )
        except Exception as e:
            renderer.print_error(f"[Error: {e}]")
        print()


async def _async_invoke_with_stream(agent, user_input, config, gate, renderer,
                                     max_retries=5, prebuilt_message: dict | None = None):
    from langgraph.types import Command
    import asyncio as _asyncio

    if prebuilt_message:
        next_input = {"messages": [prebuilt_message]}
    else:
        next_input = {"messages": [{"role": "user", "content": user_input}]}

    for retry in range(max_retries):
        try:
            events = agent.astream_events(next_input, config=config, version="v2")
            await renderer.render_stream(events)
            return
        except Exception as e:
            error_msg = str(e)
            # Check if there's an interrupt to handle (any exception might hide one)
            state = None
            try:
                state = agent.get_state(config)
            except Exception:
                pass
            interrupts = []
            if state and hasattr(state, "tasks") and state.tasks:
                for task in state.tasks:
                    if hasattr(task, "interrupts"):
                        interrupts.extend(task.interrupts)

            if not interrupts:
                if "Connection" in type(e).__name__ or "Connect" in type(e).__name__ or "nodename" in error_msg:
                    if retry < max_retries - 1:
                        await _asyncio.sleep(1.0)
                        continue
                raise

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
