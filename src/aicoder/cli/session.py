import uuid
import shutil
from pathlib import Path


class SessionManager:
    def __init__(self, sessions_dir: Path):
        self._root = sessions_dir

    def _project_dir(self, project_hash: str) -> Path:
        return self._root / project_hash

    def _session_dir(self, project_hash: str, thread_id: str) -> Path:
        return self._project_dir(project_hash) / thread_id

    def list_sessions(self, project_hash: str) -> list[dict]:
        proj_dir = self._project_dir(project_hash)
        if not proj_dir.exists():
            return []
        sessions = []
        for d in sorted(proj_dir.iterdir(), reverse=True):
            if d.is_dir():
                state_db = d / "state.db"
                sessions.append({
                    "thread_id": d.name,
                    "active": state_db.exists(),
                })
        return sessions

    def create_session(self, project_hash: str) -> str:
        thread_id = uuid.uuid4().hex[:12]
        session_dir = self._session_dir(project_hash, thread_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        return thread_id

    def delete_session(self, project_hash: str, thread_id: str):
        session_dir = self._session_dir(project_hash, thread_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)

    def get_state_db_path(self, project_hash: str, thread_id: str) -> str:
        return str(self._session_dir(project_hash, thread_id) / "state.db")

    def get_store_db_path(self, project_hash: str, thread_id: str) -> str:
        return str(self._session_dir(project_hash, thread_id) / "store.db")
