from aicoder.cli.permission_gate import PermissionGate
from aicoder.config.permissions import PermissionManager


class TestPermissionGate:
    def test_pre_approved_allowed_always(self, config_dir):
        pm = PermissionManager(config_dir)
        pm.save("/project", "ls", "allow_always")
        gate = PermissionGate(pm, "/project")
        assert gate.needs_approval("ls") is False

    def test_pre_denied(self, config_dir):
        pm = PermissionManager(config_dir)
        pm.save("/project", "rm -rf", "deny")
        gate = PermissionGate(pm, "/project")
        assert gate.is_denied("rm -rf") is True

    def test_unknown_command_needs_approval(self, config_dir):
        pm = PermissionManager(config_dir)
        gate = PermissionGate(pm, "/project")
        assert gate.needs_approval("echo hello") is True

    def test_session_allow(self, config_dir):
        pm = PermissionManager(config_dir)
        gate = PermissionGate(pm, "/project")
        gate.allow_session("npm install")
        assert gate.needs_approval("npm install") is False
        assert gate.needs_approval("npm test") is True

    def test_reset_session(self, config_dir):
        pm = PermissionManager(config_dir)
        gate = PermissionGate(pm, "/project")
        gate.allow_session("ls")
        gate.reset_session()
        assert gate.needs_approval("ls") is True
