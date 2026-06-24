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
from aicoder.agent.bash_tool import init_bash_session
from aicoder.agent.models import list_models, get_model_info, supports_vision, find_vision_model
from aicoder.agent.images import read_image, has_clipboard_image, read_clipboard_image, ImageError
from aicoder.util import project_hash, RECURSION_LIMIT


STYLE = Style.from_dict({
    "prompt": "#00ff00 bold",
    "toolbar": "bg:#333333 #ffffff",
})

bindings = KeyBindings()
SCREENSHOT_TMP = "/tmp/aicoder_screenshot.png"


@bindings.add("c-d")
def exit_app(event):
    event.app.exit()


SCREENSHOT_TMP = "/tmp/aicoder_screenshot.png"
SCREENSHOT_FLAG = "/tmp/aicoder_screenshot.flag"


@bindings.add("f2")
def screenshot(event):
    """F2: interactive screenshot. Flag file indicates pending image."""
    subprocess.run(["screencapture", "-i", SCREENSHOT_TMP],
                   check=False, stderr=subprocess.DEVNULL)
    if Path(SCREENSHOT_TMP).exists() and Path(SCREENSHOT_TMP).stat().st_size > 0:
        Path(SCREENSHOT_FLAG).touch()
        event.app.invalidate()


def _build_multimodal_message(text: str, image_b64: str, mime: str) -> dict:
    """Build a multimodal user message."""
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": text or "Analyze this image"},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
        ],
    }


def _ensure_vision_model(agent, cfg, current_model, project_root, bash_session,
                          state_db, store_db, skill_paths):
    """If current model lacks vision, auto-switch and rebuild agent. Returns (agent, new_model)."""
    if supports_vision(current_model):
        return agent, current_model

    vision_model = find_vision_model()
    if not vision_model:
        print("  No vision model available. Add one via /model or config.")
        return agent, current_model

    vm_info = get_model_info(vision_model)
    vm_display = vm_info["display"] if vm_info else vision_model

    old_info = get_model_info(current_model)
    old_display = old_info["display"] if old_info else current_model
    print(f"  Auto-switch: {old_display} -> {vm_display} (image support)")

    new_agent = _rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                                vision_model, skill_paths)
    return new_agent, vision_model


def _rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                   model_name, skill_paths=None):
    return create_agent(cfg, project_root, bash_session, state_db,
                        store_db_path=store_db, model_name=model_name,
                        skill_paths=skill_paths)


def _resolve_image(cmd_result) -> tuple[str, str] | None:
    """Parse command result for image. Returns (b64, mime, description) or None."""
    if not isinstance(cmd_result, str):
        return None
    if cmd_result.startswith("__IMAGE_FILE__"):
        payload = cmd_result[len("__IMAGE_FILE__"):]
        if "|" in payload:
            path, desc = payload.split("|", 1)
        else:
            path, desc = payload, ""
        b64, mime = read_image(path)
        print(f"  Image: {path} ({len(b64)//1024}KB, {mime})")
        return (b64, mime, desc)
    elif cmd_result == "__IMAGE_CLIPBOARD__":
        result = read_clipboard_image()
        if result:
            b64, mime = result
            print(f"  Image from clipboard ({len(b64)//1024}KB, {mime})")
            return (b64, mime, "")
        else:
            print("  No image found in clipboard")
            return None
    return None


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

    bash_session = init_bash_session(project_root, cfg.ui.max_output_lines)

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
    renderer = StreamRenderer(show_thinking=cfg.ui.show_thinking)

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

    langgraph_config = {
        "configurable": {"thread_id": str(thread_id)},
        str(RECURSION_LIMIT): RECURSION_LIMIT,
    }

    while True:
        image_b64 = None
        image_mime = None

        try:
            raw = session.prompt([("class:prompt", "> ")])
            if not isinstance(raw, str):
                continue
            user_input = raw.strip()

            # Check for pending screenshot (set by F2 key binding)
            if Path(SCREENSHOT_FLAG).exists():
                Path(SCREENSHOT_FLAG).unlink()
                if Path(SCREENSHOT_TMP).exists():
                    tag = f"/image {SCREENSHOT_TMP}"
                    if user_input:
                        user_input = f"{tag} {user_input}"
                    else:
                        user_input = tag
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            # Empty input: check clipboard for image
            if has_clipboard_image():
                result = read_clipboard_image()
                if result:
                    image_b64, image_mime = result
                    print(f"  Image from clipboard ({len(image_b64)//1024}KB, {image_mime})")
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
                b64, mime, desc = img

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

                agent, current_model = _ensure_vision_model(
                    agent, cfg, current_model, project_root, bash_session,
                    state_db, store_db, skill_paths,
                )
                cmd_handler.set_model(current_model)

                msg = _build_multimodal_message(desc, b64, mime)
                try:
                    asyncio.run(
                        _async_invoke_with_stream(agent, None, langgraph_config,
                                                   gate, renderer, prebuilt_message=msg)
                    )
                except Exception as e:
                    renderer.print_error(f"[Error: {e}]")
                print()
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
            if image_b64:
                agent, current_model = _ensure_vision_model(
                    agent, cfg, current_model, project_root, bash_session,
                    state_db, store_db, skill_paths,
                )
                cmd_handler.set_model(current_model)
                msg = _build_multimodal_message(user_input, image_b64, image_mime)
                asyncio.run(
                    _async_invoke_with_stream(agent, None, langgraph_config,
                                               gate, renderer, prebuilt_message=msg)
                )
            else:
                asyncio.run(
                    _async_invoke_with_stream(agent, user_input, langgraph_config, gate, renderer)
                )
        except Exception as e:
            renderer.print_error(f"[Error: {e}]")
        print()


async def _async_invoke_with_stream(agent, user_input, config, gate, renderer,
                                     max_retries=5, prebuilt_message: dict | None = None):
    from langgraph.types import Command

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
            if "interrupt" not in error_msg.lower() and "LangGraphInterrupt" not in type(e).__name__:
                renderer.print_error(f"[Error: {error_msg}]")
                return

        state = agent.get_state(config)
        interrupts = []
        if state and hasattr(state, "tasks") and state.tasks:
            for task in state.tasks:
                if hasattr(task, "interrupts"):
                    interrupts.extend(task.interrupts)

        if not interrupts:
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
