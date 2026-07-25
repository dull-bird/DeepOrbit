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

def _rules_dir(config: Config) -> str:
    return f"{config.dir('system')}/Rules"


def _diary_note_count(config: Config) -> int:
    root = config.path("diary")
    return len(list(root.glob("*.md"))) if root.is_dir() else 0


def evaluate_gate(context: dict, *, inbox_limit: int = 10, diary_habit_notes: int = 3) -> dict:
    """Deterministic zero-token gate: should an agent be woken at all?

    Fires only on facts the CLI can compute without a model. Rules the user
    dismissed more than accepted are suppressed (feedback loop). Returns
    {"notify": bool, "reasons": [...]}; exit-code mapping lives in the CLI.
    """
    feedback = context.get("feedback") or {}

    def suppressed(rule_id: str) -> bool:
        entry = feedback.get(rule_id) or {}
        return entry.get("dismissed", 0) > entry.get("accepted", 0) and entry.get("dismissed", 0) > 0

    reasons: list[dict] = []
    due = context.get("reminders_due") or []
    if due and not suppressed("due-reminders"):
        reasons.append({"rule": "due-reminders", "detail": f"{len(due)} 个到期提醒"})
    suggest_ids = [s.get("id") for s in context.get("suggest") or []]
    stalled = suggest_ids.count("stalled-project")
    if stalled and not suppressed("stalled-project"):
        reasons.append({"rule": "stalled-project", "detail": f"{stalled} 个项目停滞"})
    if "triage-inbox" in suggest_ids and not suppressed("triage-inbox"):
        reasons.append({"rule": "triage-inbox", "detail": f"inbox 超过 {inbox_limit} 条待处理"})
    for high in (s for s in (context.get("suggest") or []) if s.get("priority") == "high"):
        if not suppressed(high.get("id", "")):
            reasons.append({"rule": high["id"], "detail": high.get("title", "高优先级建议")})
            break
    facts = context.get("facts") or {}
    if (
        facts.get("diary_streak_days") == 0
        and facts.get("diary_note_count", 0) >= diary_habit_notes
        and not suppressed("diary-streak")
    ):
        reasons.append({"rule": "diary-streak", "detail": "日记断更"})
    return {"notify": bool(reasons), "reasons": reasons}


def load_rules(config: Config) -> list[dict]:
    """Raw WHEN-THEN rules from 99_System/Rules/*.md frontmatter.

    Tolerant by design: a missing directory or an unparseable/incomplete file
    yields an empty (or shorter) list, never an error — rules are advisory.
    """
    root = config.vault / _rules_dir(config)
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
    root = config.path("inbox")
    if not root.is_dir():
        return 0
    return len([path for path in root.glob("*.md") if path.name != "Todos.md"])


def _diary_streak_days(config: Config, today: dt.date) -> int:
    """Consecutive days with a 10_Diary note, counting back from today.

    A missing note for today does not break the streak — the day is not over.
    """
    root = config.path("diary")
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
            "diary_note_count": _diary_note_count(config),
        },
        "rules": load_rules(config),
        "feedback": acceptance_rates(),
    }
