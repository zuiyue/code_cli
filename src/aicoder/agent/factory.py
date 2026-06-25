import os
import sqlite3
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.sqlite import SqliteStore

from aicoder.config.loader import AppConfig
from aicoder.agent.prompt import build_system_prompt
from aicoder.agent.bash_tool import BashSession, create_bash_tool
from aicoder.agent.subagents import explore_subagent, general_subagent
from aicoder.agent.models import create_chat_model


def create_agent(
    cfg: AppConfig,
    project_root: str,
    bash_session: BashSession,
    state_db_path: str,
    store_db_path: str | None = None,
    model_name: str | None = None,
    skill_paths: list[str] | None = None,
    extra_tools: list | None = None,
):
    system_prompt = build_system_prompt(cfg, project_root)
    bash_tool = create_bash_tool(bash_session)

    subagents = [
        explore_subagent,
        general_subagent,
    ]

    checkpointer = MemorySaver()

    kwargs = {}
    if store_db_path:
        store_db_path_dir = os.path.dirname(store_db_path)
        if store_db_path_dir:
            os.makedirs(store_db_path_dir, exist_ok=True)
        store_conn = sqlite3.connect(store_db_path, check_same_thread=False)
        store = SqliteStore(store_conn)
        kwargs["store"] = store

    name = model_name or cfg.model.name
    model = create_chat_model(model_name=name, temperature=cfg.model.temperature)

    if skill_paths is None:
        skill_paths = ["./skills/"]

    all_tools = [bash_tool]
    if extra_tools:
        all_tools.extend(extra_tools)

    agent = create_deep_agent(
        name="aicoder",
        model=model,
        tools=all_tools,
        system_prompt=system_prompt,
        subagents=subagents,
        backend=FilesystemBackend(root_dir=project_root, virtual_mode=False),
        interrupt_on={},
        skills=skill_paths,
        checkpointer=checkpointer,
        **kwargs,
    )
    return agent
