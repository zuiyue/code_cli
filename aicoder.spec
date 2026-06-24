# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for aicoder single-file binary."""
import os
from pathlib import Path

block_cipher = None

# Collect hidden imports
hidden_imports = [
    "deepagents",
    "deepagents.graph",
    "deepagents.backends",
    "langgraph",
    "langgraph.checkpoint",
    "langgraph.checkpoint.memory",
    "langgraph.checkpoint.sqlite",
    "langgraph.store",
    "langgraph.store.sqlite",
    "langchain_openai",
    "langchain_core",
    "langsmith",
    "prompt_toolkit",
    "rich",
    "rich.live",
    "rich.layout",
    "rich.panel",
    "rich.markdown",
    "rich.text",
    "rich.console",
    "tomllib",
    "tomli",
    "tomli_w",
    "sqlite3",
    "aiosqlite",
    "tiktoken",
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
]

a = Analysis(
    ["src/aicoder/main.py"],
    pathex=[os.path.abspath("src")],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="aicoder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
