from aicoder.cli.commands import CommandHandler
from tests.conftest import FakeSessionManager


class TestModelCommand:
    def test_model_shows_current(self):
        handler = CommandHandler(FakeSessionManager())
        result = handler.handle("/model")
        assert "deepseek-chat" in result

    def test_model_switch_to_known(self):
        handler = CommandHandler(FakeSessionManager())
        result = handler.handle("/model deepseek-reasoner")
        assert "deepseek-reasoner" in result
        assert handler.current_model == "deepseek-reasoner"

    def test_model_switch_to_unknown(self):
        handler = CommandHandler(FakeSessionManager())
        result = handler.handle("/model bad-model")
        assert "Unknown model" in result
        assert handler.current_model == "deepseek-chat"

    def test_help_includes_model(self):
        handler = CommandHandler(FakeSessionManager())
        result = handler.handle("/help")
        assert "/model" in result
        assert "/models" in result
