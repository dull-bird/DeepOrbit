from __future__ import annotations

import importlib.util
import shutil

from .config import Config
from .search import SearchIndex


def diagnose(config: Config) -> dict:
    return {
        "vault": str(config.vault),
        "vault_id": config.vault_id,
        "cache": SearchIndex(config).status(),
        "capabilities": {
            "obsidian_cli": bool(shutil.which("obsidian")),
            "chromadb": importlib.util.find_spec("chromadb") is not None,
            "git": bool(shutil.which("git")),
        },
        "optional_plugins": {
            "tasks": (config.vault / ".obsidian" / "plugins" / "obsidian-tasks-plugin").exists(),
            "dataview": (config.vault / ".obsidian" / "plugins" / "dataview").exists(),
            "calendar": (config.vault / ".obsidian" / "plugins" / "calendar").exists(),
        },
    }
