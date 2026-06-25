"""HITL interrupt handlers — strategy pattern for different tool approvals."""

from abc import ABC, abstractmethod
from langgraph.types import Command

from aicoder.agent.diff import show_diff


class InterruptHandler(ABC):
    """Base class for interrupt handlers."""

    @abstractmethod
    def can_handle(self, tool_name: str, args: dict) -> bool:
        """Return True if this handler can handle the given tool call."""

    @abstractmethod
    def handle(self, tool_name: str, args: dict) -> dict:
        """Handle the interrupt. Returns a resume value for Command."""


class FileWriteHandler(InterruptHandler):
    """Show diff for write_file and edit_file operations."""

    def can_handle(self, tool_name: str, args: dict) -> bool:
        return tool_name in ("write_file", "edit_file") and bool(args.get("file_path"))

    def handle(self, tool_name: str, args: dict) -> dict:
        file_path = args.get("file_path", "")
        content = args.get("content", "")
        print(show_diff(file_path, content))
        d = input("  Write? [y]es / [n]o: ").strip().lower()
        return {"decisions": [{"type": "approve" if d == "y" else "reject"}]}


class BashApprovalHandler(InterruptHandler):
    """Permission-gate for bash commands."""

    def __init__(self, gate):
        self._gate = gate

    def can_handle(self, tool_name: str, args: dict) -> bool:
        return tool_name == "bash"

    def handle(self, tool_name: str, args: dict) -> dict:
        command = args.get("command", "")
        gate = self._gate

        if gate.is_denied(command):
            print(f"  [Denied: {command[:80]}]")
            return {"decisions": [{"type": "reject"}]}

        if not gate.needs_approval(command):
            return {"decisions": [{"type": "approve"}]}

        print(f"\n  Bash: {command[:150]}")
        d = input("  Allow? [y]es / [n]o / [a]lways: ").strip().lower()
        if d == "a":
            gate.allow_always(command)
        elif d == "y":
            gate.allow_session(command)
        approved = d in ("y", "a")
        return {"decisions": [{"type": "approve" if approved else "reject"}]}


class AutoApproveHandler(InterruptHandler):
    """Default handler: auto-approve any unknown tool."""

    def can_handle(self, tool_name: str, args: dict) -> bool:
        return True  # Catch-all

    def handle(self, tool_name: str, args: dict) -> dict:
        return {"decisions": [{"type": "approve"}]}
