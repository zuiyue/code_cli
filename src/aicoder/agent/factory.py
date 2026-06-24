import os
import sqlite3
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore
from langchain_openai import ChatOpenAI

from aicoder.config.loader import AppConfig
from aicoder.agent.prompt import build_system_prompt
from aicoder.agent.bash_tool import create_bash_tool
from aicoder.agent.subagents import explore_subagent, general_subagent


def create_agent(
    cfg: AppConfig,
    project_root: str,
    state_db_path: str,
    store_db_path: str | None = None,
):
    system_prompt = build_system_prompt(cfg, project_root)
    bash_tool = create_bash_tool(project_root)

    subagents = [
        {**explore_subagent},
        {**general_subagent},
    ]

    # SqliteSaver.from_conn_string returns a context manager; use direct connection
    db_path = os.path.dirname(state_db_path)
    if db_path:
        os.makedirs(db_path, exist_ok=True)
    conn = sqlite3.connect(state_db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    kwargs = {}
    if store_db_path:
        store_db_path_dir = os.path.dirname(store_db_path)
        if store_db_path_dir:
            os.makedirs(store_db_path_dir, exist_ok=True)
        store_conn = sqlite3.connect(store_db_path, check_same_thread=False)
        store = SqliteStore(store_conn)
        kwargs["store"] = store

    api_key = cfg.model.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
    model = ChatOpenAI(
        model=cfg.model.name,
        api_key=api_key,
        base_url=cfg.model.api_base,
        temperature=cfg.model.temperature,
    )

    agent = create_deep_agent(
        name="aicoder",
        model=model,
        tools=[bash_tool],
        system_prompt=system_prompt,
        subagents=subagents,
        backend=FilesystemBackend(root_dir=project_root, virtual_mode=False),
        interrupt_on={"bash": True},
        skills=["./skills/"],
        checkpointer=checkpointer,
        **kwargs,
    )
    return agent
