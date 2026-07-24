"""Device-local cron registry for scheduled DeepOrbit workflows.

Jobs are natural-language instructions executed by an agent (do.daily,
do.dream, …). This module owns the deterministic part: what is due, and
last-run bookkeeping. `run_due` marks a job as reported when it is returned,
so a job fires at most once per interval even if the agent never completes it.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .errors import DeepOrbitError

INTERVALS = {"hourly": 1, "daily": 24, "weekly": 168}
REGISTRY_NAME = "cron.json"


class CronError(DeepOrbitError):
    code = "CRON_ERROR"


@dataclass(slots=True)
class CronJob:
    name: str
    vault: str
    every_hours: int
    instruction: str
    last_run: str
    enabled: bool = True


def registry_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "deeporbit" / REGISTRY_NAME


def _load() -> dict:
    path = registry_path()
    if not path.exists():
        return {"jobs": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CronError(f"Invalid cron registry {path}: {exc}") from exc


def _save(data: dict) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_every(every: str) -> int:
    """'hourly' | 'daily' | 'weekly' | '<N>h' | '<N>d' → interval in hours."""
    text = every.strip().lower()
    if text in INTERVALS:
        return INTERVALS[text]
    try:
        if text.endswith("h"):
            hours = int(text[:-1])
        elif text.endswith("d"):
            hours = int(text[:-1]) * 24
        else:
            hours = int(text)
    except ValueError as exc:
        raise CronError(f"Invalid interval {every!r}; use hourly/daily/weekly or e.g. 12h, 3d") from exc
    if hours <= 0:
        raise CronError(f"Interval must be positive: {every!r}")
    return hours


def _to_job(name: str, entry: dict) -> CronJob:
    return CronJob(
        name=name,
        vault=entry["vault"],
        every_hours=entry["every_hours"],
        instruction=entry["instruction"],
        last_run=entry.get("last_run", ""),
        enabled=entry.get("enabled", True),
    )


def add_job(name: str, vault: Path | str, instruction: str, every: str) -> CronJob:
    if not name or "/" in name:
        raise CronError(f"Invalid job name: {name!r}")
    path = Path(vault).expanduser().resolve()
    if not path.is_dir():
        raise CronError(f"Vault does not exist: {path}")
    data = _load()
    data["jobs"][name] = {
        "vault": str(path),
        "every_hours": parse_every(every),
        "instruction": instruction,
        "last_run": "",
        "enabled": True,
    }
    _save(data)
    return _to_job(name, data["jobs"][name])


def list_jobs() -> list[CronJob]:
    return [_to_job(name, entry) for name, entry in sorted(_load()["jobs"].items())]


def remove_job(name: str) -> CronJob:
    data = _load()
    entry = data["jobs"].pop(name, None)
    if entry is None:
        raise CronError(f"Unknown job: {name}")
    _save(data)
    return _to_job(name, entry)


def set_enabled(name: str, enabled: bool) -> CronJob:
    data = _load()
    entry = data["jobs"].get(name)
    if entry is None:
        raise CronError(f"Unknown job: {name}")
    entry["enabled"] = enabled
    _save(data)
    return _to_job(name, entry)


def run_due(now: datetime | None = None) -> list[CronJob]:
    """Return enabled jobs whose interval elapsed; stamps their last_run."""
    now = now or datetime.now(timezone.utc)
    data = _load()
    due: list[CronJob] = []
    for name, entry in sorted(data["jobs"].items()):
        if not entry.get("enabled", True):
            continue
        last = entry.get("last_run", "")
        elapsed: timedelta | None = None
        if last:
            try:
                elapsed = now - datetime.fromisoformat(last)
            except ValueError:
                elapsed = None
        if elapsed is not None and elapsed < timedelta(hours=entry["every_hours"]):
            continue
        entry["last_run"] = now.isoformat(timespec="seconds")
        due.append(_to_job(name, entry))
    if due:
        _save(data)
    return due
