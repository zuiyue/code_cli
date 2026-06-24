# Skills 系统 — 设计文档

**日期**: 2026-06-24
**目标**: 实现技能市场系统，支持安装、加载、管理 SKILL.md 格式的技能

---

## 1. 概述

Deep Agents 内置 `SkillsMiddleware` 支持从本地目录按需加载 SKILL.md 技能。本功能在其基础上构建三层技能发现 + 远程安装 + 管理命令。

---

## 2. 三层技能来源

| 来源 | 路径 | 优先级 | 说明 |
|------|------|--------|------|
| Builtin | `<安装路径>/skills/builtin/` | 低 | 随 aicoder 发布，3 个预装技能 |
| User | `~/.aicoder/skills/` | 中 | 用户通过 `/skill install` git clone 安装 |
| Project | `./skills/` | 高 | 项目级技能，用户自行创建 |

同名技能：Project > User > Builtin 覆盖。

---

## 3. SKILL.md 格式

```markdown
---
name: python-testing
description: Python testing best practices with pytest fixtures, mocking, and async patterns
---

# Python Testing Skill

Instructions for the agent on how to write and run tests.
```

---

## 4. 组件

### SkillManager (`config/skills.py`)

| 方法 | 职责 |
|------|------|
| `discover(project_root)` → `list[SkillInfo]` | 扫描三源，返回已安装技能列表 |
| `install(git_url)` → `str` | git clone 到 user 目录，验证 SKILL.md |
| `remove(name)` → `bool` | 删除 user 目录下的技能 |
| `resolve_paths(project_root)` → `list[str]` | 返回有效目录路径列表，传给 agent |

SkillInfo: `(name, source, path, description)`

### 命令 (`cli/commands.py`)

| 命令 | 行为 |
|------|------|
| `/skills` | 列出所有已安装技能，标注来源和状态 |
| `/skill <name>` | 查看技能详情（SKILL.md 内容摘要） |
| `/skill install <git-url>` | git clone 安装 |
| `/skill remove <name>` | 删除用户安装的技能 |

### Agent Factory 改动 (`agent/factory.py`)

`skills` 参数从固定的 `["./skills/"]` 改为运行时传入的路径列表。

---

## 5. 内置技能

| 名称 | 描述 |
|------|------|
| `python-testing` | pytest 夹具、mock、异步测试最佳实践 |
| `git-workflow` | git commit 规范、分支管理、PR 流程 |
| `code-review` | 代码审查检查清单和反模式识别 |

---

## 6. 不在 v1 范围

- `/skill update` 命令（git pull 边界情况太多）
- skills.toml 索引缓存（目录扫描足够快）
- 远程市场搜索引擎
