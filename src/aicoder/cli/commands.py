class CommandHandler:
    def __init__(self, session_manager=None, sessions_dir="", project_hash="", thread_id=""):
        self._sm = session_manager
        self._sessions_dir = sessions_dir
        self._project_hash = project_hash
        self._thread_id = thread_id

    def is_command(self, text: str) -> bool:
        return text.strip().startswith("/")

    def handle(self, text: str) -> str | None:
        if not self.is_command(text):
            return None
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        if cmd == "/help":
            return self._help()
        elif cmd == "/clear":
            return self._clear()
        elif cmd == "/sessions":
            return self._sessions()
        elif cmd == "/exit":
            return "exit"
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."

    def _help(self) -> str:
        return "Available commands:\n  /help       Show this help\n  /clear      Clear current session\n  /sessions   List saved sessions\n  /exit       Exit the program"

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
