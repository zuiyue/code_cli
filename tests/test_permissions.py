from aicoder.config.permissions import PermissionManager


class TestPermissionManager:
    def test_no_existing_permissions_returns_none(self, config_dir):
        pm = PermissionManager(config_dir)
        assert pm.check("/project", "ls") is None

    def test_allow_always_remembered(self, config_dir):
        pm = PermissionManager(config_dir)
        pm.save("/project", "npm install", "allow_always")
        result = pm.check("/project", "npm install")
        assert result == "allow_always"

    def test_deny_remembered(self, config_dir):
        pm = PermissionManager(config_dir)
        pm.save("/project", "rm -rf /", "deny")
        result = pm.check("/project", "rm -rf /")
        assert result == "deny"

    def test_different_project_separate_permissions(self, config_dir):
        pm = PermissionManager(config_dir)
        pm.save("/project-a", "echo hello", "allow_always")
        assert pm.check("/project-b", "echo hello") is None

    def test_persistence_across_instances(self, config_dir):
        pm1 = PermissionManager(config_dir)
        pm1.save("/project", "git status", "allow_always")
        pm2 = PermissionManager(config_dir)
        assert pm2.check("/project", "git status") == "allow_always"

    def test_same_command_different_project(self, config_dir):
        pm = PermissionManager(config_dir)
        pm.save("/p1", "npm test", "allow_always")
        pm.save("/p2", "npm test", "deny")
        assert pm.check("/p1", "npm test") == "allow_always"
        assert pm.check("/p2", "npm test") == "deny"
