from aicoder.cli.commands import CommandHandler


class FakeSessionManager:
    def __init__(self):
        self.deleted = []
        self.sessions_data = []

    def list_sessions(self, ph):
        return self.sessions_data

    def delete_session(self, ph, tid):
        self.deleted.append(tid)


class TestModelCommand:
    def test_model_shows_current(self):
        handler = CommandHandler(FakeSessionManager(), "", "hash", "tid")
        result = handler.handle("/model")
        assert "deepseek-chat" in result

    def test_model_switch_to_known(self):
        handler = CommandHandler(FakeSessionManager(), "", "hash", "tid")
        result = handler.handle("/model deepseek-reasoner")
        assert "deepseek-reasoner" in result
        assert handler.current_model == "deepseek-reasoner"

    def test_model_switch_to_unknown(self):
        handler = CommandHandler(FakeSessionManager(), "", "hash", "tid")
        result = handler.handle("/model bad-model")
        assert "Unknown model" in result
        assert handler.current_model == "deepseek-chat"  # unchanged

    def test_help_includes_model(self):
        handler = CommandHandler(FakeSessionManager(), "", "hash", "tid")
        result = handler.handle("/help")
        assert "/model" in result
        assert "/models" in result
