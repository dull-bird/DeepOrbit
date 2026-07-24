from __future__ import annotations

import importlib.util
import shutil

from .config import Config
from .links import list_links, registry_path
from .search import SearchIndex

def diagnose(config: Config) -> dict:
    links = list_links()
    default_link = next((link.name for link in links if link.is_default), None)
    return {
        "vault": str(config.vault),
        "vault_id": config.vault_id,
        "cache": SearchIndex(config).status(),
        "links": {
            "registry": str(registry_path()),
            "count": len(links),
            "default": default_link,
            "names": [link.name for link in links],
        },
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
