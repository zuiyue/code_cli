"""Agent runtime: lifecycle management, image resolution, streaming invocation."""

import asyncio

from aicoder.agent.models import supports_vision
from aicoder.agent.vision import ImageAttachment, pick_vision_model, describe_model
from aicoder.agent.images import read_image, read_clipboard_image, ImageError
from aicoder.agent.factory import create_agent
from aicoder.cli.interrupts import FileWriteHandler, BashApprovalHandler, AutoApproveHandler

# Project root passed by REPL at startup


def ensure_vision_model(agent, cfg, current_model, project_root, bash_session,
                        state_db, store_db, skill_paths):
    """Auto-switch to vision model if needed. Returns (new_agent, new_model_name)."""
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

    new_agent = rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                              chosen, skill_paths)
    return new_agent, chosen


def resolve_image(cmd_result) -> tuple[ImageAttachment, str] | None:
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
            img = ImageAttachment(*read_image(path), source=path)
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


def rebuild_agent(cfg, project_root, bash_session, state_db, store_db,
                  model_name, skill_paths=None, extra_tools=None):
    """Recreate the agent with new model or tools."""
    return create_agent(cfg, project_root, bash_session, state_db,
                        store_db_path=store_db, model_name=model_name,
                        skill_paths=skill_paths, extra_tools=extra_tools)


async def invoke_stream(agent, user_input, config, gate, renderer,
                        max_retries=5, prebuilt_message: dict | None = None,
                        mcp_client=None, extra_tools_callback=None):
    """Invoke agent with streaming + HITL interrupt handling.

    After the stream, checks for HITL interrupts (write_file, edit_file, bash)
    and handles them with user confirmation. Retries on connection errors.
    """
    from langgraph.types import Command

    if prebuilt_message:
        next_input = {"messages": [prebuilt_message]}
    else:
        next_input = {"messages": [{"role": "user", "content": user_input}]}

    for retry in range(max_retries):
        try:
            events = agent.astream_events(next_input, config=config, version="v2")
            await renderer.render_stream(events)

            # Check for HITL interrupt after stream
            state = None
            try: state = agent.get_state(config)
            except Exception: pass
            interrupts = []
            if state and hasattr(state, "tasks") and state.tasks:
                for task in state.tasks:
                    if hasattr(task, "interrupts"):
                        interrupts.extend(task.interrupts)

            if not interrupts:
                return

            # Handle interrupts
            for interrupt in interrupts:
                val = getattr(interrupt, "value", None)
                if not isinstance(val, dict):
                    next_input = Command(resume={"decisions": [{"type": "approve"}]})
                    continue

                action_requests = val.get("action_requests", [])
                if not action_requests:
                    next_input = Command(resume={"decisions": [{"type": "approve"}]})
                    continue

                for ar in action_requests:
                    tool_name = ar.get("name", "")
                    args = ar.get("args", {})

                    # Strategy pattern: find the first handler that can handle this
                    handlers = [
                        FileWriteHandler(),
                        BashApprovalHandler(gate),
                        AutoApproveHandler(),
                    ]
                    for h in handlers:
                        if h.can_handle(tool_name, args):
                            next_input = Command(resume=h.handle(tool_name, args))
                            break

        except Exception as e:
            error_msg = str(e)
            if "Connection" in type(e).__name__ or "Connect" in type(e).__name__ or "nodename" in error_msg:
                if retry < max_retries - 1:
                    await asyncio.sleep(1.0)
                    continue
            raise

    renderer.print_error("[Max retries exceeded]")
