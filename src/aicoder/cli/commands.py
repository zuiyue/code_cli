from aicoder.agent.models import list_models, get_model_info
from prompt_toolkit.completion import Completer, Completion


ALL_COMMANDS = ["/help", "/clear", "/sessions", "/model", "/models",
                "/skills", "/skill", "/exit"]


class ModelCompleter(Completer):
    """Tab-completion for commands with context-aware completions."""
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
    def __init__(self, session_manager=None, sessions_dir="",
                 project_hash="", thread_id=""):
        self._sm = session_manager
        self._sessions_dir = sessions_dir
        self._project_hash = project_hash
        self._thread_id = thread_id
        self._current_model = "deepseek-chat"
        self._skill_manager = None
        self._project_root = "."

    @property
    def current_model(self) -> str:
        return self._current_model

    def set_model(self, name: str):
        self._current_model = name

    def set_skill_manager(self, skill_manager, project_root: str):
        self._skill_manager = skill_manager
        self._project_root = project_root

    def is_command(self, text: str) -> bool:
        return text.strip().startswith("/")

    def handle(self, text: str) -> str | None:
        if not self.is_command(text):
            return None
        parts = text.strip().split(maxsplit=2)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        arg2 = parts[2] if len(parts) > 2 else ""

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
        elif cmd == "/skills":
            return self._list_skills()
        elif cmd == "/skill":
            return self._skill(arg, arg2)
        elif cmd == "/exit":
            return "exit"
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."

    def _help(self) -> str:
        return (
            "Commands:\n"
            "  /help              Show this help\n"
            "  /clear             Clear current session\n"
            "  /sessions          List saved sessions\n"
            "  /model [name]      Show or switch model\n"
            "  /models            List available models\n"
            "  /skills            List installed skills\n"
            "  /skill <name>      Show skill details\n"
            "  /skill install <url>  Install skill from git\n"
            "  /skill remove <name>  Remove installed skill\n"
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
            avail = ", ".join(list_models())
            return f"Unknown model: {arg}\nAvailable: {avail}"

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
            src_label = {"builtin": "[builtin]", "user": "[user]", "project": "[project]"}.get(s.source, "")
            lines.append(f"  {s.name:25s} {src_label:10s} {s.description[:60]}")
        return "\n".join(lines)

    def _skill(self, arg: str, arg2: str) -> str:
        if not self._skill_manager:
            return "Skill manager not available."

        if arg == "install":
            url = arg2
            if not url:
                return "Usage: /skill install <git-url>"
            ok, msg = self._skill_manager.install(url)
            return msg

        elif arg == "remove":
            name = arg2
            if not name:
                return "Usage: /skill remove <name>"
            ok, msg = self._skill_manager.remove(name)
            return msg

        elif arg:
            # Show skill details
            content = self._skill_manager.read_skill_md(arg, self._project_root)
            if content:
                return f"\n{content}"
            return f"Skill '{arg}' not found."

        return "Usage: /skill <name> | /skill install <url> | /skill remove <name>"
