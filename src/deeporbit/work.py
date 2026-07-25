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

from .config import Config, DEFAULT_DIRS
from .errors import DeepOrbitError
from .frontmatter import read_fields, write_fields
from .tasks import parse_tasks

STATUSES = ("active", "paused", "done", "archived")
SCAN_DIRS = [*DEFAULT_DIRS, "99_System/Archive"]
SNAPSHOT_DIR = "99_System/snapshots"
TRASH_DIR = ".trash"
CANONICAL_AUTHORS = ("ai", "human", "mixed")


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
    items: list[WorkItem] = []
    for rel_dir in SCAN_DIRS:
        root = config.vault / rel_dir
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
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
    root = config.vault / SNAPSHOT_DIR
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
    path = config.vault / SNAPSHOT_DIR / f"{current['date']}.json"
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


def set_status(config: Config, path: str, status: str, *, today: date | None = None) -> WorkItem:
    if status not in STATUSES:
        raise WorkError(f"Unknown status {status!r}; expected one of {', '.join(STATUSES)}")
    target = _resolve(config, path)
    if target.is_dir():
        raise WorkError(f"Status applies to a note, not a folder: {path}")
    _check_writable(config, _rel(config, target))
    today = today or date.today()
    _bump(target, {"status": status, "updated": today.isoformat()})
    item = next((item for item in scan(config) if item.path == _rel(config, target)), None)
    if item is None:
        raise WorkError(f"Note has no frontmatter status field: {path}")
    return item


def _archive_bucket(rel: PurePosixPath) -> str:
    top = rel.parts[0]
    if top.startswith("99_System"):
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
    bucket = _archive_bucket(rel)
    if bucket == "Inbox":
        dest = config.vault / "99_System" / "Archive" / "Inbox" / f"{today:%Y}" / f"{today:%m}" / source.name
    else:
        dest = config.vault / "99_System" / "Archive" / bucket / f"{today:%Y}" / source.name
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
        and not item.path.startswith("40_Wiki/")
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


_PROTECTED_TOP = {".obsidian", ".git", TRASH_DIR, "99_System"}
_PROTECTED_FILES = {"deeporbit.json", "DeepOrbitPrompt.md"}


def trash(config: Config, path: str) -> dict:
    source = _resolve(config, path)
    if source == config.vault:
        raise WorkError("Cannot trash the vault root")
    rel = PurePosixPath(_rel(config, source))
    if rel.parts[0] in _PROTECTED_TOP or str(rel) in _PROTECTED_FILES:
        raise WorkError(f"Refusing to trash protected path: {rel}")
    _check_writable(config, str(rel))
    dest = config.vault / TRASH_DIR / rel
    if dest.exists():
        raise WorkError(f"Trash already contains {rel}; resolve the existing copy first")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
    return {"from": str(rel), "to": _rel(config, dest)}
