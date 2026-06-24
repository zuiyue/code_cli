from aicoder.agent.models import list_models, get_model_info


class CommandHandler:
    def __init__(self, session_manager=None, sessions_dir="", project_hash="", thread_id=""):
        self._sm = session_manager
        self._sessions_dir = sessions_dir
        self._project_hash = project_hash
        self._thread_id = thread_id
        self._current_model = "deepseek-chat"

    @property
    def current_model(self) -> str:
        return self._current_model

    def set_model(self, name: str):
        self._current_model = name

    def is_command(self, text: str) -> bool:
        return text.strip().startswith("/")

    def handle(self, text: str) -> str | None:
        if not self.is_command(text):
            return None
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            return self._help()
        elif cmd == "/clear":
            return self._clear()
        elif cmd == "/sessions":
            return self._sessions()
        elif cmd == "/model":
            return self._model(arg)
        elif cmd == "/models":
            return self._list_models()
        elif cmd == "/exit":
            return "exit"
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."

    def _help(self) -> str:
        return (
            "Available commands:\n"
            "  /help              Show this help\n"
            "  /clear             Clear current session\n"
            "  /sessions          List saved sessions\n"
            "  /model [name]      Show or switch model\n"
            "  /models            List available models\n"
            "  /exit              Exit the program"
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
            info = get_model_info(self._current_model)
            name = info["display"] if info else self._current_model
            return f"Current model: {self._current_model} ({name})\nUse /model <name> to switch. /models to list."

        if arg not in list_models():
            avail = ", ".join(list_models())
            return f"Unknown model: {arg}\nAvailable: {avail}"

        self._current_model = arg
        info = get_model_info(arg)
        return f"Switched to: {arg} ({info['display']})\nNote: takes effect on next message."

    def _list_models(self) -> str:
        lines = ["Available models:"]
        for name in list_models():
            info = get_model_info(name)
            marker = " (current)" if name == self._current_model else ""
            lines.append(f"  {name:25s} {info['display']} ({info['provider']}){marker}")
        return "\n".join(lines)
