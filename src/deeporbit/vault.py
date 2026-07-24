from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .config import DEFAULT_DIRS, load_config, save_readonly_dirs
from .frontmatter import read_fields
from .profile import ensure as ensure_profile

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
    workflows: list[str] = field(default_factory=list)
    system_files: list[str] = field(default_factory=list)
    guides: list[str] = field(default_factory=list)
    runtime_bundle: list[str] = field(default_factory=list)
    readonly_dirs: list[str] = field(default_factory=list)


WORKFLOW_DIR = "99_System/DeepOrbit/skills"
WORKFLOW_INDEX = "99_System/DeepOrbit/skills-index.json"
RUNTIME_BUNDLE_DIR = "99_System/DeepOrbit/repo"
RUNTIME_BUNDLE_ITEMS = (
    "AGENTS.md",
    "CLAUDE.md",
    "DeepOrbitPrompt.md",
    "README.md",
    "README_CN.md",
    "LICENSE",
    "pyproject.toml",
    "package.json",
    "gemini-extension.json",
    "kimi.plugin.json",
    ".mcp.json",
    ".claude-plugin",
    ".codex-plugin",
    ".codex/hooks",
    ".omp/hooks",
    "hooks",
    "skills",
    "commands",
    "src",
    "scripts/hooks",
    "mcp",
    "docs",
    "99_System",
)
RUNTIME_BUNDLE_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "site/dist",
    "site/.astro",
    "*.egg-info",
    "skills-lock.json",
)
WEREAD_MARKERS = ("微信读书", "weread")


def _detect_readonly_dirs(root: Path, config_dirs: list[str]) -> list[str]:
    """Detect externally managed folders (e.g. weread-vault exports).

    A directory qualifies when at least 3 sampled notes carry WeRead
    frontmatter (`source: 微信读书` or a `book_id`), or its name is a known
    export folder name. Existing configured zones are preserved.
    """
    zones = set(config_dirs)
    candidates = [p for p in root.iterdir() if p.is_dir()]
    candidates += [p for base in list(candidates) if base.is_dir() for p in base.iterdir() if p.is_dir()]
    for directory in candidates:
        if directory.name.startswith(".") or directory.name == "99_System":
            continue
        named = any(marker in directory.name for marker in WEREAD_MARKERS)
        hits = 0
        for note in sorted(directory.glob("*.md"))[:10]:
            fields = read_fields(note.read_text(encoding="utf-8", errors="replace"))
            if fields.get("book_id") or fields.get("source") == "微信读书":
                hits += 1
        if hits >= 3 or (named and hits >= 1):
            rel = str(directory.relative_to(root))
            if not any(rel == z or rel.startswith(z.rstrip("/") + "/") for z in zones):
                zones.add(rel)
    return sorted(zones)


def _default_skills_source() -> Path | None:
    candidate = Path(__file__).resolve().parents[2] / "skills"
    return candidate if candidate.is_dir() else None


def _default_system_source() -> Path | None:
    candidate = Path(__file__).resolve().parents[2] / "99_System"
    return candidate if candidate.is_dir() else None


def _default_repo_source() -> Path | None:
    candidate = Path(__file__).resolve().parents[2]
    return candidate if (candidate / "skills").is_dir() and (candidate / "src" / "deeporbit").is_dir() else None


def _copy_runtime_item(source: Path, target: Path) -> str | None:
    if not source.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, ignore=RUNTIME_BUNDLE_IGNORE)
    else:
        shutil.copy2(source, target)
    return str(target)


def sync_runtime_bundle(root: Path, source: Path) -> list[str]:
    """Copy the portable repository surface into the vault.

    This is a curated runtime bundle, not a Git checkout: it includes skills,
    commands, prompts, hooks, CLI source, MCP, docs, and manifests, while
    excluding caches, virtualenvs, build outputs, and lock/generated agent
    install directories.
    """
    source = source.expanduser().resolve()
    target = root / RUNTIME_BUNDLE_DIR
    if source == root or source in root.parents:
        return []
    if target.exists():
        shutil.rmtree(target)
    copied: list[str] = []
    for rel in RUNTIME_BUNDLE_ITEMS:
        item = _copy_runtime_item(source / rel, target / rel)
        if item:
            copied.append(str(Path(item).relative_to(root)))
    return copied


def _overlay_system_files(root: Path, source: Path) -> list[str]:
    """Copy missing Templates/Bases/Prompts into the vault; never overwrite."""
    added: list[str] = []
    for item in sorted(source.rglob("*")):
        if item.is_dir():
            continue
        rel = item.relative_to(source)
        dest = root / "99_System" / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
            added.append(str(Path("99_System") / rel))
    return added


GUIDE_FILES = ("methodology.md", "tooling-landscape.md")


def _default_guides_source() -> Path | None:
    candidate = Path(__file__).resolve().parents[2] / "docs"
    return candidate if candidate.is_dir() else None


def _sync_guides(root: Path, source: Path) -> list[str]:
    """Refresh the mentor guides inside the vault (derived copies, overwritten)."""
    target = root / "99_System" / "DeepOrbit" / "guides"
    synced: list[str] = []
    for name in GUIDE_FILES:
        src = source / name
        if not src.is_file():
            continue
        target.mkdir(parents=True, exist_ok=True)
        dest = target / name
        if not dest.exists() or dest.read_bytes() != src.read_bytes():
            shutil.copy2(src, dest)
        synced.append(name)
    return synced


def _frontmatter_field(text: str, key: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    for line in text[3:end].splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip() or None
    return None


def sync_workflows(root: Path, source: Path) -> list[str]:
    """Copy the workflow skills into the vault and rebuild the trigger index.

    The vault copy is derived data: the repository `skills/` tree is the source
    of truth, so the target directory is replaced wholesale on every sync.
    """
    target = root / WORKFLOW_DIR
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", ".*"))
    index: list[dict] = []
    for skill_md in sorted(target.glob("do.*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        index.append(
            {
                "name": _frontmatter_field(text, "name") or skill_md.parent.name,
                "description": _frontmatter_field(text, "description") or "",
            }
        )
    (root / WORKFLOW_INDEX).write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return [entry["name"] for entry in index]


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


def initialize(
    vault: Path | str,
    *,
    migrate: bool = True,
    skills_source: Path | str | None = None,
    repo_source: Path | str | None = None,
) -> InitResult:
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
    config = load_config(root, create=True)
    if ensure_profile(config).created:
        created.append("99_System/Profile.md")
    repo = Path(repo_source).expanduser().resolve() if repo_source else _default_repo_source()
    workflows: list[str] = []
    source = Path(skills_source).expanduser().resolve() if skills_source else (repo / "skills" if repo else _default_skills_source())
    if source and source.is_dir():
        workflows = sync_workflows(root, source)
    system_files: list[str] = []
    system_source = (repo / "99_System" if repo and (repo / "99_System").is_dir() else _default_system_source())
    if system_source:
        system_files = _overlay_system_files(root, system_source)
    guides: list[str] = []
    guides_source = (repo / "docs" if repo and (repo / "docs").is_dir() else _default_guides_source())
    if guides_source:
        guides = _sync_guides(root, guides_source)
    runtime_bundle: list[str] = []
    if repo and repo.is_dir():
        runtime_bundle = sync_runtime_bundle(root, repo)
    readonly_dirs = _detect_readonly_dirs(root, config.readonly_dirs)
    if readonly_dirs != config.readonly_dirs:
        save_readonly_dirs(root, readonly_dirs)
    return InitResult(created, migrated, conflicts, workflows, system_files, guides, runtime_bundle, readonly_dirs)
