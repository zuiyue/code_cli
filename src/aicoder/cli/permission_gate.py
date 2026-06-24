from aicoder.config.permissions import PermissionManager


class PermissionGate:
    def __init__(self, permission_manager: PermissionManager, project_root: str):
        self._pm = permission_manager
        self._project_root = project_root
        self._session_allowed: set[str] = set()

    def needs_approval(self, command: str) -> bool:
        if self.is_denied(command):
            return False
        decision = self._pm.check(self._project_root, command)
        if decision == "allow_always":
            return False
        if command in self._session_allowed:
            return False
        return True

    def is_denied(self, command: str) -> bool:
        decision = self._pm.check(self._project_root, command)
        return decision == "deny"

    def allow_session(self, command: str):
        self._session_allowed.add(command)

    def allow_always(self, command: str):
        self._pm.save(self._project_root, command, "allow_always")

    def reset_session(self):
        self._session_allowed.clear()
