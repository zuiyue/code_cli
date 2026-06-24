from aicoder.cli.commands import CommandHandler
from tests.conftest import FakeSessionManager


class TestCommandHandler:
    def test_is_command_detects_slash(self):
        handler = CommandHandler()
        assert handler.is_command("/help") is True
        assert handler.is_command("not a command") is False

    def test_help_returns_info(self):
        handler = CommandHandler()
        result = handler.handle("/help")
        assert "help" in result.lower()
        assert "clear" in result.lower()

    def test_clear_deletes_session(self, temp_dir):
        fake_sm = FakeSessionManager()
        handler = CommandHandler(fake_sm, temp_dir, "test-hash", thread_id="abc")
        result = handler.handle("/clear")
        assert "cleared" in result.lower()

    def test_unknown_command(self):
        handler = CommandHandler()
        result = handler.handle("/foobar")
        assert "unknown" in result.lower()

    def test_non_command_passes_through(self):
        handler = CommandHandler()
        result = handler.handle("write a function")
        assert result is None
