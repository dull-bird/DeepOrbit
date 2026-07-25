"""Proactive-companion context pack: the deterministic half of do.heartbeat.

`deeporbit heartbeat` gathers everything an agent needs for one patrol:
suggestions, lifecycle counts, due reminders (checked, never delivered),
progress delta against the latest snapshot, cheap pre-screened facts, the raw
WHEN rules from 99_System/Rules, and per-rule feedback acceptance rates.

It never writes to the vault: propose-approve means the agent proposes and
the user approves. Silent by default — an empty context pack is HEARTBEAT_OK.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict

from .config import Config
from .frontmatter import read_fields
from .remind import check as due_reminders
from .suggest import acceptance_rates, suggest
from .work import live_delta, overview

RULES_DIR = "99_System/Rules"


def load_rules(config: Config) -> list[dict]:
    """Raw WHEN-THEN rules from 99_System/Rules/*.md frontmatter.

    Tolerant by design: a missing directory or an unparseable/incomplete file
    yields an empty (or shorter) list, never an error — rules are advisory.
    """
    root = config.vault / RULES_DIR
    if not root.is_dir():
        return []
    rules: list[dict] = []
    for path in sorted(root.glob("*.md")):
        try:
            fields = read_fields(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        when, then = fields.get("when", ""), fields.get("then", "")
        if not (when and then):
            continue
        rules.append(
            {
                "name": fields.get("name") or path.stem,
                "when": when,
                "then": then,
                "path": str(path.relative_to(config.vault)),
            }
        )
    return rules


def _inbox_note_count(config: Config) -> int:
    root = config.vault / "00_Inbox"
    if not root.is_dir():
        return 0
    return len([path for path in root.glob("*.md") if path.name != "Todos.md"])


def _diary_streak_days(config: Config, today: dt.date) -> int:
    """Consecutive days with a 10_Diary note, counting back from today.

    A missing note for today does not break the streak — the day is not over.
    """
    root = config.vault / "10_Diary"
    if not root.is_dir():
        return 0
    day = today
    if not (root / f"{day.isoformat()}.md").exists():
        day -= dt.timedelta(days=1)
    streak = 0
    while (root / f"{day.isoformat()}.md").exists():
        streak += 1
        day -= dt.timedelta(days=1)
    return streak


def build_context(config: Config, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now()
    today = now.date()
    suggestions = suggest(config, today=today)
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "suggest": [asdict(item) for item in suggestions],
        "status": overview(config)["counts"],
        "reminders_due": [asdict(task) for task in due_reminders(config, now)],
        "snapshot_delta": live_delta(config, today=today),
        "facts": {
            "stalled_projects": sum(1 for item in suggestions if item.id == "stalled-project"),
            "inbox_note_count": _inbox_note_count(config),
            "diary_streak_days": _diary_streak_days(config, today),
        },
        "rules": load_rules(config),
        "feedback": acceptance_rates(),
    }
