from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import DEFAULT_DIRS, load_config

SYSTEM_DIRS = [
    "50_Resources/Newsletters",
    "50_Resources/Product_Launches",
    "50_Resources/News",
    "99_System/Templates",
    "99_System/Prompts",
    "99_System/Archive",
    "99_System/Bases",
    "99_System/Calendar",
]

MIGRATIONS = {
    "50_Resources/产品发布": "50_Resources/Product_Launches",
    "50_Resources/新闻": "50_Resources/News",
    "99_System/提示词": "99_System/Prompts",
    "99_System/归档": "99_System/Archive",
}


@dataclass(slots=True)
class InitResult:
    created: list[str]
    migrated: list[str]
    conflicts: list[str]


def _merge_directory(source: Path, target: Path, root: Path) -> tuple[list[str], list[str]]:
    migrated: list[str] = []
    conflicts: list[str] = []
    target.mkdir(parents=True, exist_ok=True)
    for item in sorted(source.rglob("*")):
        rel = item.relative_to(source)
        dest = target / rel
        if item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        elif dest.exists():
            if item.read_bytes() != dest.read_bytes():
                conflicts.append(str(item.relative_to(root)))
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(dest))
            migrated.append(str(dest.relative_to(root)))
    for directory in sorted((p for p in source.rglob("*") if p.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    if source.exists() and not any(source.iterdir()):
        source.rmdir()
    return migrated, conflicts


def initialize(vault: Path | str, *, migrate: bool = True) -> InitResult:
    root = Path(vault).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for rel in [*DEFAULT_DIRS, "99_System", *SYSTEM_DIRS]:
        path = root / rel
        if not path.exists():
            path.mkdir(parents=True)
            created.append(rel)
    migrated: list[str] = []
    conflicts: list[str] = []
    if migrate:
        for old_rel, new_rel in MIGRATIONS.items():
            old = root / old_rel
            if old.is_dir():
                moved, collided = _merge_directory(old, root / new_rel, root)
                migrated.extend(moved)
                conflicts.extend(collided)
    load_config(root, create=True)
    return InitResult(created, migrated, conflicts)
