"""Generalized work-item lifecycle for the whole vault.

A *work item* is any Markdown note with a `status:` frontmatter field, anywhere
in the managed folders — projects, research, writings, resources, inbox. The
lifecycle vocabulary is `active | paused | done | archived`; other values
(`draft`, `processed`, …) are reported but never rewritten by transitions.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path, PurePosixPath

from .config import STATUS_SECTIONS, STATUS_SUBDIRS, Config, DIRECTORIES
from .errors import DeepOrbitError
from .frontmatter import read_fields, write_fields
from .tasks import parse_tasks

STATUSES = ("active", "paused", "done", "archived")
TRASH_DIR = ".trash"
CANONICAL_AUTHORS = ("ai", "human", "mixed")

# Status subfolders inside STATUS_SECTIONS (projects/research): paused items
# live in <section>/Paused/, archived in <section>/Archived/; active stays at
# the section root. Names come from config.STATUS_* in config.py.
PAUSED_SUBDIR, ARCHIVED_SUBDIR = STATUS_SUBDIRS


def _scan_dirs(config: Config) -> list[str]:
    keys = ("inbox", "diary", "writings", "projects", "research", "wiki", "resources", "notes", "family", "plans")
    return [config.dir(key) for key in keys] + [f"{config.dir('system')}/Archive"]


def _snapshot_dir(config: Config) -> str:
    return f"{config.dir('system')}/snapshots"


def _section_of(config: Config, rel: str) -> str | None:
    """Logical status-section name when `rel` sits under that configured dir."""
    top = rel.split("/", 1)[0]
    for section in STATUS_SECTIONS:
        if config.dir(section) == top:
            return section
    return None


def _author(fields: dict[str, str], readonly: bool) -> str:
    """Normalize authorship; foreign uses of `author` (e.g. book authors in
    weread-vault exports) are external sync content, not note authorship."""
    raw = fields.get("author", "")
    if raw in CANONICAL_AUTHORS:
        return raw
    return "external" if readonly else "human"


class WorkError(DeepOrbitError):
    code = "WORK_ERROR"


@dataclass(slots=True)
class WorkItem:
    path: str
    title: str
    status: str
    area: str
    updated: str
    author: str
    readonly: bool = False
    mtime: str = ""  # ISO date of last file modification; activity fallback


def is_readonly(config: Config, rel: str) -> bool:
    """True when `rel` sits inside an externally managed read-only zone."""
    for zone in config.readonly_dirs:
        if rel == zone or rel.startswith(zone.rstrip("/") + "/"):
            return True
    return False


def _check_writable(config: Config, rel: str) -> None:
    if is_readonly(config, rel):
        raise WorkError(
            f"Read-only zone (managed by an external sync such as weread-vault): {rel}. "
            "Link to it instead of modifying; adjust `readonly.directories` in deeporbit.json to change this."
        )


def _title(text: str, fields: dict[str, str], stem: str) -> str:
    if fields.get("title"):
        return fields["title"]
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return stem


def scan(config: Config) -> list[WorkItem]:
    # Reads are network-bound on cloud-synced vaults (iCloud materializes
    # evicted files on read, seconds per file): read concurrently, but keep
    # the output order deterministic by sorting paths first.
    from concurrent.futures import ThreadPoolExecutor

    paths: list[Path] = []
    for rel_dir in _scan_dirs(config):
        root = config.vault / rel_dir
        if root.is_dir():
            paths.extend(sorted(root.rglob("*.md")))

    def _read(path: Path):
        try:
            return path, path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return path, ""

    with ThreadPoolExecutor(max_workers=8) as pool:
        texts = dict(pool.map(_read, paths))

    items: list[WorkItem] = []
    for path in paths:
        text = texts[path]
        fields = read_fields(text)
        status = fields.get("status", "")
        if not status:
            continue
        rel = str(path.relative_to(config.vault))
        readonly = is_readonly(config, rel)
        items.append(
            WorkItem(
                path=rel,
                title=_title(text, fields, path.stem),
                status=status,
                area=fields.get("area", ""),
                updated=fields.get("updated", ""),
                author=_author(fields, readonly),
                readonly=readonly,
                mtime=date.fromtimestamp(path.stat().st_mtime).isoformat(),
            )
        )
    return items


def overview(config: Config) -> dict:
    items = scan(config)
    counts: dict[str, int] = {}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return {
        "counts": dict(sorted(counts.items())),
        "items": [asdict(item) for item in items],
    }


# --- progress snapshots ------------------------------------------------------
#
# Snapshots give the lifecycle a time dimension: one JSON per day under
# 99_System/snapshots (knowledge, not cache — they live in the vault and
# sync with it). Writing is idempotent per day (same-day overwrite), and the
# interesting output is the delta against the previous snapshot.


def _todo_counts(config: Config) -> dict:
    tasks = parse_tasks(config)
    return {
        "total": len(tasks),
        "open": sum(1 for task in tasks if task.status in ("todo", "doing")),
        "done": sum(1 for task in tasks if task.status == "done"),
    }


def build_snapshot(config: Config, *, today: date | None = None) -> dict:
    today = today or date.today()
    items = scan(config)
    counts = {status: 0 for status in STATUSES}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return {
        "date": today.isoformat(),
        "counts": counts,
        "items": [{"path": item.path, "status": item.status, "updated": item.updated} for item in items],
        "todos": _todo_counts(config),
    }


def load_snapshots(config: Config) -> list[dict]:
    """All on-disk snapshots, ascending by date; corrupt files are skipped."""
    root = config.vault / _snapshot_dir(config)
    if not root.is_dir():
        return []
    snapshots: list[dict] = []
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("date"):
            snapshots.append(data)
    return snapshots


def snapshot_delta(current: dict, previous: dict | None) -> dict | None:
    """Newly activated / newly completed items and new done-todo count."""
    if previous is None:
        return None
    prev_status = {item.get("path"): item.get("status", "") for item in previous.get("items", [])}
    activated = [
        item["path"]
        for item in current.get("items", [])
        if item.get("status") == "active" and prev_status.get(item.get("path")) != "active"
    ]
    completed = [
        item["path"]
        for item in current.get("items", [])
        if item.get("status") in ("done", "archived")
        and prev_status.get(item.get("path")) not in ("done", "archived")
    ]
    return {
        "since": previous.get("date"),
        "activated": activated,
        "completed": completed,
        "done_todos": current.get("todos", {}).get("done", 0) - previous.get("todos", {}).get("done", 0),
    }


def write_snapshot(config: Config, *, today: date | None = None) -> dict:
    """Persist today's snapshot (same-day overwrite) and diff vs the previous day."""
    today = today or date.today()
    current = build_snapshot(config, today=today)
    previous: dict | None = None
    for snap in load_snapshots(config):
        if snap["date"] < current["date"]:
            previous = snap
    path = config.vault / _snapshot_dir(config) / f"{current['date']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "snapshot": str(path.relative_to(config.vault)),
        **current,
        "delta": snapshot_delta(current, previous),
    }


def live_delta(config: Config, *, today: date | None = None) -> dict | None:
    """Delta of the live state against the latest on-disk snapshot, without writing."""
    today = today or date.today()
    snapshots = [snap for snap in load_snapshots(config) if snap["date"] <= today.isoformat()]
    previous = snapshots[-1] if snapshots else None
    return snapshot_delta(build_snapshot(config, today=today), previous)


def _resolve(config: Config, path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = config.vault / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(config.vault):
        raise WorkError(f"Path escapes the vault: {path}")
    if not candidate.exists():
        raise WorkError(f"Path does not exist: {path}")
    return candidate


def _rel(config: Config, path: Path) -> str:
    return str(path.relative_to(config.vault))


def _bump(path: Path, updates: dict[str, str]) -> None:
    path.write_text(write_fields(path.read_text(encoding="utf-8"), updates), encoding="utf-8")


def _move_item(config: Config, item: Path, dest_dir: Path) -> Path:
    """Move a file-or-folder work item into dest_dir, never overwriting.

    A file-form item brings its same-stem asset folder along (the same
    wholesale move archive uses for folder-form items).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / item.name
    if dest.exists():
        raise WorkError(f"Target already exists, nothing overwritten: {_rel(config, dest)}")
    assets = item.parent / item.stem if item.is_file() else None
    if assets is not None and assets.is_dir() and (dest_dir / assets.name).exists():
        raise WorkError(f"Target already exists, nothing overwritten: {_rel(config, dest_dir / assets.name)}")
    shutil.move(str(item), str(dest))
    if assets is not None and assets.is_dir():
        shutil.move(str(assets), str(dest_dir / assets.name))
    return dest


def _container_of(note: Path) -> Path:
    """Folder-form projects (X/X.md) move as a whole folder; plain notes alone."""
    return note.parent if note.parent.name == note.stem else note


def _filing_of(config: Config, container: Path, section: str) -> str | None:
    """Where the container sits inside the section: None = root, else the status subdir."""
    parts = container.relative_to(config.vault).parts
    root_depth = len(config.dir(section).split("/"))
    if len(parts) == root_depth + 1:
        return None
    if len(parts) == root_depth + 2 and parts[root_depth] in STATUS_SUBDIRS:
        return parts[root_depth]
    return "nested"


def _relocate_for_status(config: Config, note: Path, status: str) -> Path:
    """File a section item by status: paused → Paused/, active → section root.

    Other statuses and items outside STATUS_SECTIONS never move. Returns the
    (possibly new) note path.
    """
    if status not in ("active", "paused"):
        return note
    section = _section_of(config, _rel(config, note))
    if section is None:
        return note
    container = _container_of(note)
    filing = _filing_of(config, container, section)
    if filing == "nested":
        return note
    desired = PAUSED_SUBDIR if status == "paused" else None
    if filing == desired:
        return note
    dest_dir = config.path(section) / desired if desired else config.path(section)
    is_dir = container.is_dir()
    moved = _move_item(config, container, dest_dir)
    return moved / note.name if is_dir else moved


def set_status(config: Config, path: str, status: str, *, today: date | None = None) -> WorkItem:
    if status not in STATUSES:
        raise WorkError(f"Unknown status {status!r}; expected one of {', '.join(STATUSES)}")
    target = _resolve(config, path)
    if target.is_dir():
        raise WorkError(f"Status applies to a note, not a folder: {path}")
    _check_writable(config, _rel(config, target))
    today = today or date.today()
    target = _relocate_for_status(config, target, status)
    _bump(target, {"status": status, "updated": today.isoformat()})
    item = next((item for item in scan(config) if item.path == _rel(config, target)), None)
    if item is None:
        raise WorkError(f"Note has no frontmatter status field: {path}")
    return item


def _archive_bucket(config: Config, rel: PurePosixPath) -> str:
    top = rel.parts[0]
    if top in (config.dir("system"), DIRECTORIES["system"]):
        return rel.parts[2] if len(rel.parts) > 2 else "Misc"
    stripped = top.split("_", 1)[1] if "_" in top and top.split("_", 1)[0].isdigit() else top
    return stripped or "Misc"


def archive(config: Config, path: str, *, today: date | None = None) -> dict:
    source = _resolve(config, path)
    if source == config.vault:
        raise WorkError("Cannot archive the vault root")
    rel = PurePosixPath(_rel(config, source))
    _check_writable(config, str(rel))
    today = today or date.today()
    section = _section_of(config, str(rel))
    if section is not None:
        # Status-folder sections file archived work in place.
        dest = config.path(section) / ARCHIVED_SUBDIR / source.name
    else:
        bucket = _archive_bucket(config, rel)
        system = config.dir("system")
        if rel.parts[0] == config.dir("inbox"):
            dest = config.vault / system / "Archive" / bucket / f"{today:%Y}" / f"{today:%m}" / source.name
        else:
            dest = config.vault / system / "Archive" / bucket / f"{today:%Y}" / source.name
    if dest.exists():
        raise WorkError(f"Archive target already exists, nothing overwritten: {_rel(config, dest)}")
    if source.is_file() and source.suffix == ".md":
        _bump(source, {"status": "archived", "archived": today.isoformat(), "updated": today.isoformat()})
    elif source.is_dir():
        for note in sorted(source.rglob("*.md")):
            _bump(note, {"status": "archived", "archived": today.isoformat(), "updated": today.isoformat()})
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
    return {"from": str(rel), "to": _rel(config, dest), "status": "archived", "archived": today.isoformat()}


def _activity_date(item: WorkItem) -> date | None:
    for raw in (item.updated, item.mtime):
        try:
            return date.fromisoformat(str(raw).strip().strip('"').strip("'")[:10])
        except ValueError:
            continue
    return None


def sweep(config: Config, *, days: int = 60, dry_run: bool = False, today: date | None = None) -> dict:
    """Auto-pause active items idle for more than `days` days.

    Exclusions mirror the manual triage rules: read-only zones and 40_Wiki
    (timeless reference) are never swept.
    """
    today = today or date.today()
    candidates = [
        item
        for item in scan(config)
        if not item.readonly
        and item.status == "active"
        and not item.path.startswith(config.dir("wiki") + "/")
        and (activity := _activity_date(item)) is not None
        and (today - activity).days > days
    ]
    paused: list[str] = []
    if not dry_run:
        for item in candidates:
            set_status(config, item.path, "paused")
            paused.append(item.path)
    return {
        "days": days,
        "dry_run": dry_run,
        "matched": [item.path for item in candidates],
        "paused": paused,
    }


def organize(config: Config, *, dry_run: bool = True) -> dict:
    """Re-file every projects/research work item by its frontmatter status.

    active → section root, paused → <section>/Paused/, archived → <section>/Archived/.
    Other statuses and nested items are left alone. Conflicts (target name
    already taken) are reported, never overwritten.
    """
    moves: list[dict] = []
    conflicts: list[str] = []
    for section in STATUS_SECTIONS:
        root = config.path(section)
        if not root.is_dir():
            continue
        desired_of = {"active": None, "paused": PAUSED_SUBDIR, "archived": ARCHIVED_SUBDIR}
        for item in scan(config):
            if item.path.split("/", 1)[0] != config.dir(section) or item.status not in desired_of:
                continue
            note = config.vault / item.path
            container = _container_of(note)
            filing = _filing_of(config, container, section)
            if filing == "nested":
                continue
            desired = desired_of[item.status]
            if filing == desired:
                continue
            dest_dir = root / desired if desired else root
            dest = dest_dir / container.name
            entry = {
                "from": _rel(config, container),
                "to": _rel(config, dest),
                "status": item.status,
            }
            if dest.exists():
                conflicts.append(f"{_rel(config, dest)} already exists; {entry['from']} left in place")
                continue
            moves.append(entry)
            if not dry_run:
                _move_item(config, container, dest_dir)
    return {"dry_run": dry_run, "moves": moves, "conflicts": conflicts}


_PROTECTED_FILES = {"deeporbit.json", "DeepOrbitPrompt.md"}


def _protected_top(config: Config) -> set[str]:
    return {".obsidian", ".git", TRASH_DIR, config.dir("system"), DIRECTORIES["system"]}


def trash(config: Config, path: str) -> dict:
    source = _resolve(config, path)
    if source == config.vault:
        raise WorkError("Cannot trash the vault root")
    rel = PurePosixPath(_rel(config, source))
    if rel.parts[0] in _protected_top(config) or str(rel) in _PROTECTED_FILES:
        raise WorkError(f"Refusing to trash protected path: {rel}")
    _check_writable(config, str(rel))
    dest = config.vault / TRASH_DIR / rel
    if dest.exists():
        raise WorkError(f"Trash already contains {rel}; resolve the existing copy first")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
    return {"from": str(rel), "to": _rel(config, dest)}
