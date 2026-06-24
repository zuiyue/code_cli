import time
from aicoder.cli.session import SessionManager


class TestSessionManager:
    def test_list_empty_sessions(self, temp_dir):
        sm = SessionManager(temp_dir / "sessions")
        sessions = sm.list_sessions("hash123")
        assert sessions == []

    def test_create_and_list_session(self, temp_dir):
        sm = SessionManager(temp_dir / "sessions")
        tid = sm.create_session("hash123")
        sessions = sm.list_sessions("hash123")
        assert len(sessions) == 1
        assert sessions[0]["thread_id"] == tid

    def test_delete_session(self, temp_dir):
        sm = SessionManager(temp_dir / "sessions")
        tid = sm.create_session("hash123")
        sm.delete_session("hash123", tid)
        assert sm.list_sessions("hash123") == []

    def test_multiple_sessions(self, temp_dir):
        sm = SessionManager(temp_dir / "sessions")
        t1 = sm.create_session("hash123")
        time.sleep(0.01)
        t2 = sm.create_session("hash123")
        sessions = sm.list_sessions("hash123")
        assert len(sessions) == 2

    def test_sessions_separated_by_project(self, temp_dir):
        sm = SessionManager(temp_dir / "sessions")
        sm.create_session("hash-a")
        sm.create_session("hash-b")
        assert len(sm.list_sessions("hash-a")) == 1
        assert len(sm.list_sessions("hash-b")) == 1

    def test_get_state_db_path(self, temp_dir):
        sm = SessionManager(temp_dir / "sessions")
        tid = sm.create_session("hash123")
        path = sm.get_state_db_path("hash123", tid)
        assert path.endswith("state.db")
        assert "hash123" in str(path)
        assert tid in str(path)
