# DeepAgent Claude Code Clone — 设计文档

**日期**: 2026-06-24
**目标**: 使用 Deep Agents 构建类 Claude Code 的终端编程助手，v1 可日常使用

---

## 1. 概述

构建一个终端 CLI 编程助手，用户通过命令行与 AI 对话，完成软件工程任务（读写文件、执行命令、搜索代码、子智能体分派）。底层以 Deep Agents 为框架引擎，上层自建 CLI 交互外壳。

### 核心理念

- **Deep Agents 提供引擎**：规划、文件系统、子智能体、技能、记忆 — 开箱即用
- **自建 CLI 交互层**：REPL、流式渲染、权限审批、配置管理
- **Bash 工具自定义**：最核心也最危险的工具，自建并配审批

**注**：文档中 `~/.<app>/` 为占位符，应用名称待定，实现时替换为实际目录名（如 `~/.aicoder/`）。

### 不在 v1 范围

- 多模型后端热切换（v1 仅 Anthropic）
- 远程/团队协作
- GUI / Web 界面
- 打包分发（PyPI / npm / Homebrew）
- VS Code / JetBrains 插件

---

## 2. 整体架构

```
┌──────────────────────────────────────────────────────┐
│                CLI Shell (prompt_toolkit + rich)       │
│  REPL  │  StreamRenderer  │  PermissionGate  │  Cmds  │
├──────────────────────────────────────────────────────┤
│                  Agent Core (create_deep_agent)        │
│  TodoList  │  Filesystem  │  BashTool(custom)         │
│  SubAgent  │  Skills      │  HITL Middleware           │
├──────────────────────────────────────────────────────┤
│              Session & Persistence                     │
│  SqliteSaver(state.db) │ SqliteStore(store.db)         │
│  config.toml  │  permissions.toml  │  AGENTS.md        │
└──────────────────────────────────────────────────────┘
```

三层，从上到下依次是交互、引擎、持久化。每层职责单一，接口清晰。

---

## 3. 模块设计

### 3.1 CLI Shell（外壳层）

**职责**：用户输入入口、流式输出渲染、权限审批交互、元命令处理、会话管理

**组件**：

| 组件 | 职责 | 实现 |
|------|------|------|
| REPL | 多行输入（Alt+Enter 换行）、历史记录（上下箭头）、Tab 补全 | `prompt_toolkit` |
| StreamRenderer | 消费 LangGraph `astream_events()` 流，分三个面板渲染：(1) Thinking (2) Tool Call (3) Output | `rich` Live 布局 |
| CommandHandler | `/help`, `/clear`, `/model`, `/config`, `/sessions` — 不经过 Agent 的元命令 | 自建路由表 |
| PermissionGate | Bash 等危险工具执行前弹出审批，返回 deny / allow_once / allow_always / allow_session | `prompt_toolkit` 快捷键弹窗 |
| SessionManager | 会话列表/新建/恢复/删除，管理 state.db 生命周期 | 文件扫描 + LangGraph config 注入 |

**流式渲染策略**：

- 使用 `agent.astream_events()` 获取事件流
- 事件类型 → 渲染映射：
  - `on_chat_model_stream` → Thinking 面板（LLM 思考内容）
  - `on_tool_start` → Tool Call 面板（工具名 + 参数）
  - `on_tool_end` → Output 面板（工具返回结果，截断超长内容）
  - `on_chat_model_end` → 最终回复
- Rich `Live` 上下文管理器自动刷新，多面板动态更新

**权限审批流程**：

当 HITL Middleware 触发 `interrupt_on={"bash": True}` 时：
1. Agent 执行暂停，进入等待状态
2. PermissionGate 通过 prompt_toolkit 弹出审批界面，展示命令内容 + 工作目录
3. 用户选择 deny / allow_once / allow_always / allow_session
4. 通过 `Command(resume={"decision": <choice>})` 恢复执行
5. allow_always 写入 `permissions.toml`

**元命令**：

| 命令 | 功能 |
|------|------|
| `/help` | 帮助 |
| `/clear` | 清空当前会话 |
| `/model <name>` | 切换模型（预留，v1 仅支持默认） |
| `/sessions` | 列出/切换历史会话 |
| `/exit` 或 Ctrl+D | 退出 |

---

### 3.2 Agent Core（引擎层）

**职责**：通过 `create_deep_agent()` 组装所有中间件和工具，暴露统一 invoke/stream 接口

**Deep Agents 自带的中间件（无需开发）**：

| 中间件 | 提供的工具/能力 |
|--------|----------------|
| TodoListMiddleware | `write_todos` — 任务分解和跟踪 |
| FilesystemMiddleware | `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep` |
| SubAgentMiddleware | `task` — 派生子智能体执行子树任务 |
| SkillsMiddleware | 从 `./skills/` 目录按需加载技能 SKILL.md |

**自定义工具和中间件**：

#### BashTool（自定义 tool）

```python
@tool
def bash(command: str, timeout: int = 120000) -> str:
    """Execute a bash command. Long-running commands timeout after 2 minutes."""
```

设计要点：
- **持久 shell**：维护一个 subprocess.Popen 实例（按 session 生命周期），连续命令共享同一工作目录和环境
- **工作目录锁定**：只能在项目根目录及其子目录下执行，禁止 `cd /` 逃逸。与 `FilesystemBackend(root_dir=project_root)` 共享同一 root，确保 Bash 和 Filesystem 工具在同一沙箱范围内运作
- **超时 kill**：超时后 `process.kill()`，返回已捕获的输出 + 超时提示
- **输出截断**：超过 500 行自动截断，完整内容写入临时文件 `~/.<app>/tmp/`，Agent 可通过 Filesystem 工具读取
- **命令白名单**：`config.toml` 的 `[bash].allowed_commands` 可配置，空 = 允许全部

#### PermissionManager（权限管理）

位于 CLI Shell 层，在 HITL interrupt 触发时由 PermissionGate 调用。

存储位置：`~/.<app>/permissions.toml`

```toml
[projects."/Users/zuiyue/workspace/myproject"]
"npm install" = "allow_always"
"rm -rf" = "deny"
```

策略层级：
1. `deny` — 命令 hash 匹配 → 直接拒绝
2. `allow_always` — 命令 hash 匹配 → 直接放行
3. `allow_session` — 当前会话内已授权 → 放行
4. 无匹配 → 触发 HITL 审批

命令 hash 算法：`sha256(location + command_text)`，确保同项目同命令不重复审批。

#### SubAgents（子智能体）

两个预定义子智能体，随 `create_deep_agent()` 注入：

| 子智能体 | 能力 | 限制 |
|---------|------|------|
| `explore` | `ls`, `read_file`, `glob`, `grep` | 禁用 bash，仅代码探索 |
| `general` | 全部工具（包含 bash） | 用于复杂多步任务 |

#### System Prompt 拼接

系统提示词由三部分组成，按优先级拼接：

```python
system_prompt = (
    base_instructions +           # Deep Agents 自带指令
    "\n\n" + project_agents_md +  # 项目根 AGENTS.md 内容（如有）
    "\n\n" + user_custom_rules    # config.toml [prompt] 额外指令
)
```

#### Agent 实例化

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore

agent = create_deep_agent(
    name="code-assistant",
    model="claude-sonnet-4-5-20250929",
    tools=[bash_tool],
    system_prompt=system_prompt,
    subagents=[explore_subagent, general_subagent],
    backend=FilesystemBackend(root_dir=project_root, virtual_mode=False),
    interrupt_on={"bash": True},
    skills=["./skills/"],
    checkpointer=SqliteSaver.from_conn_string(state_db_path),
    store=SqliteStore.from_conn_string(store_db_path),
)
```

---

### 3.3 Session & Persistence（持久化层）

**目录结构**：

```
~/.<app>/
├── config.toml              # 用户全局配置
├── permissions.toml         # 审批策略持久化
├── history/
│   └── <project-hash>.jsonl # 对话历史（可读备份）
├── sessions/
│   └── <project-hash>/
│       ├── state.db         # SqliteSaver — LangGraph 图状态
│       └── store.db         # SqliteStore — 跨 thread 持久记忆
└── tmp/                     # bash 输出溢出文件
```

#### SessionManager

| 功能 | 实现方式 |
|------|---------|
| 会话列表 | 扫描 `sessions/` 目录下所有 state.db，读取 metadata |
| 会话恢复 | `config = {"configurable": {"thread_id": <id>}}`，LangGraph 自动恢复 |
| 新建会话 | 生成 UUID thread_id，创建新 state.db |
| 会话切换 | `/sessions` 交互或 `--continue` 启动参数 |
| 会话删除 | `/clear` 删除 state.db，重置 thread |

#### 配置文件 (config.toml)

```toml
[model]
provider = "anthropic"
name = "claude-sonnet-4-5-20250929"
api_key_env = "ANTHROPIC_API_KEY"

[bash]
timeout_ms = 120000
allowed_commands = []      # 空表示全部允许

[ui]
theme = "dark"
show_thinking = true
max_output_lines = 500

[prompt]
extra_rules = ""           # 额外注入的全局系统指令

[project]
root = "."                  # 默认当前目录
auto_load_agents_md = true
```

#### AGENTS.md

启动时自动读取项目根目录 `AGENTS.md`，内容注入 system_prompt。格式与 Claude Code / opencode 兼容。

---

## 4. 数据流

### 4.1 主交互循环

```
用户输入 → REPL → 是否为 / 命令？
                      ├─ 是 → CommandHandler → 执行本地命令 → 返回结果
                      └─ 否 → agent.astream_events(messages, config)
                                │
                      ┌─────────┴─────────┐
                      │  StreamRenderer    │
                      │  (Rich Live 渲染)  │
                      └─────────┬─────────┘
                                │
                      ┌─────────┴─────────┐
                      │  遇到 bash 工具？   │
                      │  → HITL interupt  │
                      │  → PermissionGate │
                      │  → Command(resume)│
                      └─────────┬─────────┘
                                │
                      Agent 完成 → 显示最终回复
```

### 4.2 启动流程

```
1. 解析 CLI 参数 (--continue, --model, --project)
2. 加载 config.toml
3. 读取项目 AGENTS.md
4. 初始化 bash 持久 shell
5. 创建 create_deep_agent(...)
6. 如有 --continue → 加载已有 thread_id
7. 进入 REPL 循环
```

---

## 5. 错误处理

| 场景 | 处理 |
|------|------|
| API 调用失败 | 重试 3 次指数退避，最终显示错误信息，不崩溃 |
| Bash 命令超时 | kill 进程，返回部分输出 + "Command timed out" |
| Bash 命令逃逸 | 沙箱拒绝，返回 "Permission denied: outside workspace" |
| Checkpointer 损坏 | 提示用户 `/clear` 重建，记录原文件备份 |
| 配置文件损坏 | 使用默认值 + 警告，不阻止启动 |
| 流式事件异常 | 降级为非流式模式，display 完整结果 |
| 用户 Ctrl+C | 优雅退出，保存当前会话状态 |

---

## 6. 测试策略

| 层级 | 测试方式 | 覆盖重点 |
|------|---------|---------|
| BashTool | 单元测试 | 命令执行、超时、沙箱拦截、输出截断 |
| PermissionManager | 单元测试 | deny/allow 策略匹配、TOML 读写 |
| StreamRenderer | 集成测试 | 模拟事件流的渲染输出 |
| Agent Core | 集成测试 | 端到端对话流程（mock LLM） |
| CLI Shell | E2E 测试 | 用 pexpect 模拟终端交互 |

测试框架：`pytest`

---

## 7. 技术栈

| 组件 | 选型 | 理由 |
|------|------|------|
| Agent 框架 | `deepagents` (Python) | 内置规划/文件/子智能体/技能 |
| LLM Provider | Anthropic Claude | `claude-sonnet-4-5-20250929` |
| 图运行时 | `langgraph` | Deep Agents 底层 |
| 状态持久化 | `langgraph.checkpoint.sqlite.SqliteSaver` | 零依赖，文件级持久化 |
| 记忆存储 | `langgraph.store.sqlite.SqliteStore` | 跨 session 记忆 |
| CLI 框架 | `prompt_toolkit` + `rich` | REPL 交互 + 终端美化的标准组合 |
| 配置解析 | `tomli` / `tomli-w` | Python 标准 TOML |
| 测试 | `pytest` + `pexpect` | 单元 + E2E |
| Python 版本 | 3.11+ | Deep Agents 最低要求 |

---

## 8. 开放问题（v2 考虑）

- MCP (Model Context Protocol) 工具集成
- 多模型后端切换
- 自定义技能市场/社区共享
- 会话导出/分享
- 打包为单文件可执行程序 (PyInstaller / Nuitka)
