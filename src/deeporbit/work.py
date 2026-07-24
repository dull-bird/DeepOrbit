"""Generalized work-item lifecycle for the whole vault.

A *work item* is any Markdown note with a `status:` frontmatter field, anywhere
in the managed folders — projects, research, writings, resources, inbox. The
lifecycle vocabulary is `active | paused | done | archived`; other values
(`draft`, `processed`, …) are reported but never rewritten by transitions.
"""

from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path, PurePosixPath

from .config import Config, DEFAULT_DIRS
from .errors import DeepOrbitError
from .frontmatter import read_fields, write_fields

STATUSES = ("active", "paused", "done", "archived")
SCAN_DIRS = [*DEFAULT_DIRS, "99_System/Archive"]
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
