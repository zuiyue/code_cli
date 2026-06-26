# aaaa

**Language:** Python
**Build:** hatchling/pip

## Commands

- **Test:** `pytest tests/`
- **Install:** `make install`
- **Lint:** `make lint`
- **Build:** `make build`

## Structure

```
├── docs/
│   └── superpowers/
│       └── specs/
├── src/
│   └── aicoder/
│       ├── agent/
│       ├── cli/
│       ├── config/
│       ├── skills/
│       ├── __init__.py
│       ├── main.py
│       └── util.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_bash_tool.py
│   ├── test_commands.py
│   ├── test_config.py
│   ├── test_integration.py
│   ├── test_model_commands.py
│   ├── test_models.py
│   ├── test_permission_gate.py
│   ├── test_permissions.py
│   ├── test_prompt.py
│   ├── test_session.py
│   ├── test_skills.py
│   └── test_vision.py
├── vscode/
│   ├── extension.js
│   └── package.json
├── work/
│   ├── q/
│   │   └── snake.py
│   └── qqq/
│       ├── snake_game.py
│       └── story.txt
├── Makefile
├── aicoder.spec
└── pyproject.toml
```

## Conventions

- Tests use pytest
- Python 3.11+ syntax (use pathlib, f-strings, type hints)
- work/ directory is gitignored (temp files)

## Instructions

Always read relevant files before making changes.
Run tests after each change. Commit with conventional commits (feat:/fix:/refactor:).
Test with: `pytest tests/`