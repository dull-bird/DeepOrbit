from __future__ import annotations

import importlib.util
import shutil

from .config import CONFIG_NAME, DIRECTORIES, Config, skeleton_dirs
from .links import list_links, registry_path
from .search import SearchIndex

# Entries allowed at the vault root beyond the skeleton top-level dirs.
ROOT_WHITELIST_FILES = (CONFIG_NAME, "CLAUDE.md", "AGENTS.md")
ROOT_WHITELIST_PREFIXES = ("DeepOrbitPrompt.md",)


def skeleton_report(config: Config) -> dict:
    """Skeleton existence + root hygiene.

    skeleton_missing: configured skeleton dirs (incl. Paused/Archived) absent
    on disk. skeleton_violations: root entries outside the whitelist — the
    skeleton top-level dir names, config/agent files, and dot-prefixed
    entries (.obsidian, .trash, .git, .DS_Store, …).
    """
    missing = [rel for rel in skeleton_dirs(config.directories) if not (config.vault / rel).is_dir()]
    top_names = {config.dir(key) for key in DIRECTORIES}
    top_names.add(DIRECTORIES["system"])  # literal materialization tree
    violations: list[str] = []
    for entry in sorted(config.vault.iterdir()):
        name = entry.name
        if name.startswith(".") or name in top_names or name in ROOT_WHITELIST_FILES:
            continue
        if any(name.startswith(prefix) for prefix in ROOT_WHITELIST_PREFIXES):
            continue
        violations.append(name)
    return {"skeleton_missing": missing, "skeleton_violations": violations}


def diagnose(config: Config) -> dict:
    links = list_links()
    default_link = next((link.name for link in links if link.is_default), None)
    return {
        "vault": str(config.vault),
        "vault_id": config.vault_id,
        **skeleton_report(config),
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
