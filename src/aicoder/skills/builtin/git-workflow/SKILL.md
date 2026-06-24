---
name: git-workflow
description: Git commit conventions, branch management, and PR workflow for clean version control.
---

# Git Workflow

## When to Use
- Committing changes
- Creating branches
- Writing commit messages

## Instructions

### Commit Convention
Use conventional commits: `type: description`

Types: feat, fix, refactor, test, docs, chore

### Branch Naming
- `feat/<name>` for features
- `fix/<name>` for bug fixes

### Commit Flow
1. `git status`
2. `git add <files>` (not `git add -A` unless sure)
3. `git diff --staged`
4. `git commit -m "type: message"`
5. `git push`

### Never commit
- Secrets, API keys, passwords
- Large binary files
- Generated code without source
