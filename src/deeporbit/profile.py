"""User profile management — the vault's picture of who it serves.

The profile lives at `99_System/Profile.md`: flat frontmatter fields for stable
facts (role, language, domains, preferences) and an `## Observations` section
where the agent records timestamped, source-tagged learnings so the picture
gets sharper with use. User-authored frontmatter is never rewritten by
`observe`; only explicit `set` calls change it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import Config
from .frontmatter import read_fields, write_fields

PROFILE_PATH = "99_System/Profile.md"
OBSERVATIONS_HEADER = "## Observations"

DEFAULT_PROFILE = """---
role:
language: zh-CN
domains: []
preferences: []
---

# User Profile

Stable facts live in frontmatter; the agent maintains timestamped observations
below as it learns from daily work.

## Focus

## Observations
"""


@dataclass(slots=True)
class ProfileResult:
    path: str
    created: bool = False


def ensure(config: Config) -> ProfileResult:
    path = config.vault / PROFILE_PATH
    if path.exists():
        return ProfileResult(PROFILE_PATH, created=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_PROFILE, encoding="utf-8")
    return ProfileResult(PROFILE_PATH, created=True)


def show(config: Config) -> dict:
    result = ensure(config)
    text = (config.vault / PROFILE_PATH).read_text(encoding="utf-8")
    return {
        "path": result.path,
        "fields": read_fields(text),
        "observations": _observations(text),
    }


def set_field(config: Config, key: str, value: str) -> dict:
    result = ensure(config)
    path = config.vault / PROFILE_PATH
    path.write_text(write_fields(path.read_text(encoding="utf-8"), {key: value}), encoding="utf-8")
    return {"path": result.path, "fields": read_fields(path.read_text(encoding="utf-8"))}


def observe(config: Config, text: str, *, source: str = "agent", today: date | None = None) -> dict:
    if source not in ("agent", "user"):
        raise ValueError(f"source must be 'agent' or 'user', got {source!r}")
    result = ensure(config)
    path = config.vault / PROFILE_PATH
    entry = f"- [{today or date.today():%Y-%m-%d}] ({source}) {text}"
    path.write_text(_append_observation(path.read_text(encoding="utf-8"), entry), encoding="utf-8")
    return {"path": result.path, "added": entry}


FOCUS_HEADER = "## Focus"


def set_focus(config: Config, text: str) -> dict:
    """Replace the Focus section with a distilled identity summary (dream output)."""
    result = ensure(config)
    path = config.vault / PROFILE_PATH
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index(FOCUS_HEADER) + 1
    except ValueError:
        start = None
    if start is None:
        lines.append("")
        lines.append(FOCUS_HEADER)
        start = len(lines)
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    lines[start:end] = ["", text, ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"path": result.path, "focus": text}


def compact(config: Config, *, today: date | None = None) -> dict:
    """Archive raw observations to 99_System/Archive/Profile/ and reset the section.

    Called after a dream pass has distilled observations into Focus, so the
    profile stays short while the raw material stays recoverable.
    """
    result = ensure(config)
    path = config.vault / PROFILE_PATH
    text = path.read_text(encoding="utf-8")
    entries = _observations(text)
    if not entries:
        return {"path": result.path, "archived": 0}
    archive_dir = config.vault / "99_System" / "Archive" / "Profile"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = (today or date.today()).isoformat()
    archive_file = archive_dir / f"observations-{stamp}.md"
    existing = archive_file.read_text(encoding="utf-8") if archive_file.exists() else f"# Profile observations archived {stamp}\n\n"
    archive_file.write_text(existing + "\n".join(entries) + "\n", encoding="utf-8")
    lines = text.splitlines()
    start = lines.index(OBSERVATIONS_HEADER) + 1
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    lines[start:end] = [""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"path": result.path, "archived": len(entries), "archive": str(archive_file.relative_to(config.vault))}


def _observations(text: str) -> list[str]:
    lines = text.splitlines()
    try:
        start = lines.index(OBSERVATIONS_HEADER) + 1
    except ValueError:
        return []
    entries: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.strip().startswith("- "):
            entries.append(line.strip())
    return entries


def _append_observation(text: str, entry: str) -> str:
    lines = text.splitlines()
    if OBSERVATIONS_HEADER not in lines:
        suffix = "" if text.endswith("\n") else "\n"
        return f"{text}{suffix}\n{OBSERVATIONS_HEADER}\n\n{entry}\n"
    start = lines.index(OBSERVATIONS_HEADER) + 1
    insert_at = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            insert_at = i
            break
    while insert_at > start and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines[insert_at:insert_at] = [entry]
    return "\n".join(lines) + "\n"
