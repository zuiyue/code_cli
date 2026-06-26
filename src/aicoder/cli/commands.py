from aicoder.agent.models import list_models, get_model_info
from prompt_toolkit.completion import Completer, Completion


ALL_COMMANDS = ["/help", "/clear", "/sessions", "/model", "/models",
                "/skills", "/skill", "/image", "/stats", "/export",
                "/mcp", "/init", "/plan", "/build", "/exit"]


class ModelCompleter(Completer):
    def __init__(self):
        self._models = list_models()
        self._skill_names: list[str] = []

    def set_skill_names(self, names: list[str]):
        self._skill_names = names

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/model "):
            prefix = text.split(" ", 1)[1] if " " in text else ""
            for m in self._models:
                if m.startswith(prefix):
                    yield Completion(m, start_position=-len(prefix))
        elif text.startswith("/skill ") and "install" not in text and "remove" not in text:
            parts = text.split(" ")
            if len(parts) == 2:
                prefix = parts[1]
                for s in self._skill_names:
                    if s.startswith(prefix):
                        yield Completion(s, start_position=-len(prefix))
        elif text.startswith("/"):
            prefix = text
            for c in ALL_COMMANDS:
                if c.startswith(prefix):
                    yield Completion(c, start_position=-len(prefix))


class CommandHandler:
    def __init__(self, session_manager=None, sessions_dir=None,
                 project_hash=None, thread_id=None):
        self._sm = session_manager
        self._sessions_dir = sessions_dir or ""
        self._project_hash = project_hash or ""
        self._thread_id = thread_id or ""
        self._current_model = "deepseek-chat"
        self._skill_manager = None
        self._project_root = "."
        self._token_tracker = None
        self._export_agent = None
        self._export_config = None
        self._mcp_client = None
        self._plan_mode = False

    @property
    def current_model(self) -> str:
        return self._current_model

    def set_model(self, name: str):
        self._current_model = name

    def set_skill_manager(self, skill_manager, project_root: str):
        self._skill_manager = skill_manager
        self._project_root = project_root

    def set_token_tracker(self, tracker):
        self._token_tracker = tracker

    def set_export_context(self, agent, langgraph_config):
        self._export_agent = agent
        self._export_config = langgraph_config

    def set_mcp_client(self, client):
        self._mcp_client = client

    @property
    def plan_mode(self) -> bool:
        return self._plan_mode

    def is_command(self, text: str) -> bool:
        return text.strip().startswith("/")

    def handle(self, text: str) -> str | None:
        if not self.is_command(text):
            return None
        parts = text.strip().split(maxsplit=2)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        arg2 = parts[2] if len(parts) > 2 else ""

        handlers = {
            "/help": self._help,
            "/clear": self._clear,
            "/sessions": self._sessions,
            "/model": lambda: self._model(arg),
            "/models": self._list_models,
            "/skills": self._list_skills,
            "/skill": lambda: self._skill(arg, arg2),
            "/image": lambda: self._image(arg),
            "/stats": self._stats,
            "/export": lambda: self._export(arg),
            "/mcp": lambda: self._mcp(arg, arg2),
            "/init": self._init_project,
            "/plan": self._toggle_plan,
            "/build": self._toggle_plan,
            "/exit": lambda: "exit",
        }
        handler = handlers.get(cmd)
        if handler:
            return handler()
        return f"Unknown command: {cmd}. Type /help for available commands."

    def _help(self) -> str:
        return (
            "Commands:\n"
            "  Esc+Enter          Insert newline for multi-line input\n"
            "  /help              Show this help\n"
            "  /clear             Clear current session\n"
            "  /sessions          List saved sessions\n"
            "  /model [name]      Show or switch model\n"
            "  /models            List available models\n"
            "  /skills            List installed skills\n"
            "  /skill <name>      Show skill details\n"
            "  /skill install <url>  Install skill from git\n"
            "  /skill remove <name>  Remove installed skill\n"
            "  /image [path]      Attach an image (F2 to screenshot)\n"
            "  /stats             Show token usage statistics\n"
            "  /export [format]   Export conversation (md/json)\n"
            "  /mcp list          List MCP servers\n"
            "  /mcp connect <cmd> Connect MCP server\n"
            "  /init              Analyze project and create AGENTS.md\n"
            "  /plan              Plan mode (no execution)\n"
            "  /build             Build mode (execute)\n"
            "  /exit              Exit"
        )

    def _clear(self) -> str:
        if self._sm and self._project_hash and self._thread_id:
            self._sm.delete_session(self._project_hash, self._thread_id)
            return f"Session {self._thread_id} cleared."
        return "No active session to clear."

    def _sessions(self) -> str:
        if self._sm:
            sessions = self._sm.list_sessions(self._project_hash)
            if not sessions:
                return "No saved sessions."
            lines = ["Saved sessions:"]
            for s in sessions:
                marker = " (active)" if s.get("active") else ""
                lines.append(f"  - {s['thread_id']}{marker}")
            return "\n".join(lines)
        return "Session manager not available."

    def _model(self, arg: str) -> str:
        if not arg:
            models = list_models()
            info = get_model_info(self._current_model)
            name = info["display"] if info else self._current_model
            lines = [f"\n  Current: {self._current_model} ({name})", "  Models:"]
            for i, m in enumerate(models, 1):
                marker = " >>>" if m == self._current_model else ""
                mi = get_model_info(m)
                lines.append(f"    {i}. {m} ({mi['display']}){marker}")
            lines.append("\n  Type number or model name to switch, Enter to cancel.")
            return "\n".join(lines)

        if arg not in list_models():
            return f"Unknown model: {arg}\nAvailable: {', '.join(list_models())}"

        self._current_model = arg
        info = get_model_info(arg)
        return f"Switched to: {arg} ({info['display']})\nTakes effect on next message."

    def _list_models(self) -> str:
        lines = ["Available models:"]
        for name in list_models():
            info = get_model_info(name)
            marker = " (current)" if name == self._current_model else ""
            lines.append(f"  {name:25s} {info['display']} ({info['provider']}){marker}")
        return "\n".join(lines)

    def _list_skills(self) -> str:
        if not self._skill_manager:
            return "Skill manager not available."
        skills = self._skill_manager.discover(self._project_root)
        if not skills:
            return "No skills installed. Use /skill install <git-url> to add one."
        lines = ["Installed skills:"]
        for s in skills:
            src = {"builtin": "[builtin]", "user": "[user]", "project": "[project]"}.get(s.source, "")
            lines.append(f"  {s.name:25s} {src:10s} {s.description[:60]}")
        return "\n".join(lines)

    def _skill(self, arg: str, arg2: str) -> str:
        if not self._skill_manager:
            return "Skill manager not available."

        if arg == "install":
            if not arg2:
                return "Usage: /skill install <git-url>"
            _, msg = self._skill_manager.install(arg2)
            return msg

        elif arg == "remove":
            if not arg2:
                return "Usage: /skill remove <name>"
            _, msg = self._skill_manager.remove(arg2)
            return msg

        elif arg:
            content = self._skill_manager.read_skill_md(arg, self._project_root)
            if content:
                return f"\n{content}"
            return f"Skill '{arg}' not found."

        return "Usage: /skill <name> | /skill install <url> | /skill remove <name>"

    def _stats(self) -> str:
        if self._token_tracker:
            return self._token_tracker.summary()
        return "No usage data yet."

    def _export(self, fmt: str) -> str:
        if not self._export_agent:
            return "Export not available."

        fmt = (fmt or "md").lower()
        if fmt not in ("md", "json"):
            return "Usage: /export [md|json]"

        import json, os
        from datetime import datetime
        from pathlib import Path

        try:
            state = self._export_agent.get_state(self._export_config)
            msgs = state.values.get("messages", []) if state else []
        except Exception:
            return "Could not read conversation state."

        if not msgs:
            return "No messages to export."

        export_dir = Path(os.path.expanduser("~/.aicoder/exports"))
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if fmt == "json":
            data = {"messages": [{"role": getattr(m, "type", "unknown"),
                                  "content": getattr(m, "content", str(m))} for m in msgs]}
            path = export_dir / f"session_{timestamp}.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            return f"Exported: {path}"

        # Markdown
        lines = ["# Conversation Export\n"]
        for m in msgs:
            role = getattr(m, "type", "unknown")
            content = getattr(m, "content", str(m))
            if role == "human":
                lines.append(f"## You\n\n{content}\n")
            elif role == "ai":
                if content:
                    lines.append(f"## Assistant\n\n{content}\n")
            elif role == "tool" and content:
                lines.append(f"> Tool: {content[:200]}\n")
        path = export_dir / f"session_{timestamp}.md"
        path.write_text("\n".join(lines))
        return f"Exported: {path}"

    def _mcp(self, action: str, arg: str) -> str:
        if not self._mcp_client:
            return "MCP client not available."
        if action == "list":
            servers = self._mcp_client.list_servers()
            if not servers:
                return "No MCP servers connected.\nUse /mcp connect <name> <command> [args...]"
            lines = ["Connected MCP servers:"]
            for s in servers:
                lines.append(f"  {s['name']}: {s['command']} ({s['tools']} tools)")
            return "\n".join(lines)
        elif action == "connect":
            # arg = "name command args..."
            parts = arg.split(None, 1) if arg else []
            if len(parts) < 2:
                return "Usage: /mcp connect <name> <command> [args...]\nExample: /mcp connect fs npx -y @modelcontextprotocol/server-filesystem /tmp"
            name = parts[0]
            cmd_parts = parts[1].split()
            command = cmd_parts[0]
            args = cmd_parts[1:] if len(cmd_parts) > 1 else []
            return f"__MCP__CONNECT__{name}|{command}|{' '.join(args)}"
        elif action == "disconnect":
            return f"__MCP__DISCONNECT__{arg}"
        return "Usage: /mcp [list|connect|disconnect]"

    def _init_project(self) -> str:
        try:
            from pathlib import Path
            from aicoder.agent.init_project import analyze_project
            content = analyze_project(self._project_root)
            path = Path(self._project_root) / "AGENTS.md"
            path.write_text(content)
            return f"AGENTS.md created at {path}\n\n{content[:300]}..."
        except Exception as e:
            return f"Failed: {e}"

    def _toggle_plan(self) -> str:
        self._plan_mode = not self._plan_mode
        if self._plan_mode:
            return "__PLAN_MODE_ON__"
        return "Build mode — all tools enabled."

    def _image(self, arg: str) -> str:
        """Return image file path. Description in arg2 handled by REPL."""
        if not arg:
            return "__IMAGE_CLIPBOARD__"
        # Split path from optional description
        parts = arg.split(None, 1)
        path = parts[0]
        desc = parts[1] if len(parts) > 1 else ""
        if desc:
            return f"__IMAGE_FILE__{path}|{desc}"
        return f"__IMAGE_FILE__{path}"
