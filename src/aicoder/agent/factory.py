from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore

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

    checkpointer = SqliteSaver.from_conn_string(state_db_path)

    kwargs = {}
    if store_db_path:
        store = SqliteStore.from_conn_string(store_db_path)
        kwargs["store"] = store

    agent = create_deep_agent(
        name="aicoder",
        model=cfg.model.name,
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
