"""Deterministic vault-state heuristics that produce prioritized suggestions.

This is the seed for mentor coaching and the dreaming pass: it reads only
observable state (work items, index status, profile, diary) and never invents
advice. Every suggestion carries the concrete action that resolves it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .config import Config
from .hygiene import scan_hygiene
from .profile import show as profile_show
from .search import SearchIndex
from .work import scan

DORMANT_DAYS = 21
STALE_PAUSED_DAYS = 60
INBOX_LIMIT = 10


@dataclass(slots=True)
class Suggestion:
    id: str
    priority: str  # "high" | "medium" | "low"
    title: str
    detail: str
    action: str


def _parse_date(raw: str) -> date | None:
    try:
        return date.fromisoformat(raw.strip().strip('"').strip("'")[:10])
    except ValueError:
        return None


def _activity_date(item) -> date | None:
    """Curated `updated` first, file mtime as the honest fallback."""
    return _parse_date(item.updated) or _parse_date(item.mtime)


def suggest(
    config: Config,
    *,
    today: date | None = None,
    dormant_days: int = DORMANT_DAYS,
    stale_paused_days: int = STALE_PAUSED_DAYS,
    inbox_limit: int = INBOX_LIMIT,
) -> list[Suggestion]:
    today = today or date.today()
    items = [item for item in scan(config) if not item.readonly]
    out: list[Suggestion] = []
    # 40_Wiki is timeless reference (Zettelkasten layer), not lifecycle work:
    # a `status` there is noise, never a dormancy/archival signal.
    work_items = [item for item in items if not item.path.startswith("40_Wiki/")]

    done = [item for item in work_items if item.status == "done"]
    if done:
        out.append(
            Suggestion(
                id="archive-done",
                priority="high",
                title=f"Archive {len(done)} completed item(s)",
                detail=", ".join(item.title for item in done[:5]),
                action="Run /do:archive to move done work into 99_System/Archive",
            )
        )

    dormant = [
        item
        for item in work_items
        if item.status == "active"
        and (updated := _activity_date(item)) is not None
        and (today - updated) > timedelta(days=dormant_days)
    ]
    if dormant:
        out.append(
            Suggestion(
                id="pause-dormant",
                priority="medium",
                title=f"{len(dormant)} active item(s) untouched for {dormant_days}+ days",
                detail=", ".join(item.title for item in dormant[:5]),
                action="Review: deeporbit --vault . pause <path> what is dormant, or set a next action",
            )
        )

    stale_paused = [
        item
        for item in work_items
        if item.status == "paused"
        and (updated := _activity_date(item)) is not None
        and (today - updated) > timedelta(days=stale_paused_days)
    ]
    if stale_paused:
        out.append(
            Suggestion(
                id="decide-stale-paused",
                priority="medium",
                title=f"{len(stale_paused)} paused item(s) older than {stale_paused_days} days",
                detail=", ".join(item.title for item in stale_paused[:5]),
                action="Decide: resume with a concrete next action, or archive",
            )
        )

    inbox = [
        path
        for path in (config.vault / "00_Inbox").glob("*.md")
        if path.name != "Todos.md"
    ] if (config.vault / "00_Inbox").is_dir() else []
    if len(inbox) > inbox_limit:
        out.append(
            Suggestion(
                id="triage-inbox",
                priority="medium",
                title=f"Inbox holds {len(inbox)} items (limit {inbox_limit})",
                detail="Unprocessed captures pile up and hide what matters",
                action="Triage with /do:kickoff or archive processed ones",
            )
        )

    status = SearchIndex(config).status()
    if status.get("stale"):
        out.append(
            Suggestion(
                id="refresh-index",
                priority="low",
                title="Search index is stale",
                detail=f"{status.get('changed', '?')} file(s) changed since last index",
                action="deeporbit --vault . index ensure",
            )
        )

    fields = profile_show(config)["fields"]
    if not fields.get("role") or fields.get("domains") in ("", "[]"):
        out.append(
            Suggestion(
                id="complete-profile",
                priority="low",
                title="User profile is mostly empty",
                detail="A filled profile makes mentor advice and summaries personal",
                action="deeporbit --vault . profile set role \"...\" and set domains \"[...]\"",
            )
        )

    if not (config.vault / "10_Diary" / f"{today.isoformat()}.md").exists():
        out.append(
            Suggestion(
                id="start-daily",
                priority="low",
                title="No daily note for today",
                detail="Daily notes anchor agenda, recap, and dreaming",
                action="Run /do:daily to open today",
            )
        )

    findings = scan_hygiene(config)
    if findings:
        out.append(
            Suggestion(
                id="vault-cleanup-reminder",
                priority="medium",
                title=f"Vault hygiene needs attention ({len(findings)} issue(s))",
                detail=", ".join(f.path for f in findings[:5]),
                action="Run /do:organize to review and clean up the vault",
            )
        )
    out.extend(hygiene_suggestions(config))

    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda s: (order[s.priority], s.id))
    return out


def hygiene_suggestions(config: Config) -> list[Suggestion]:
    """Attachment and code-in-vault violations as actionable suggestions."""
    findings = scan_hygiene(config)
    code = [f for f in findings if f.kind in ("code-dir", "code-file")]
    attachments = [f for f in findings if f.kind.endswith("attachment")]
    out: list[Suggestion] = []
    if code:
        out.append(
            Suggestion(
                id="code-in-vault",
                priority="high",
                title=f"{len(code)} code file(s)/dir(s) inside the vault",
                detail=", ".join(f.path for f in code[:5]),
                action="Move code to a repo; leave pointer notes. Run: deeporbit --vault . hygiene",
            )
        )
    if attachments:
        out.append(
            Suggestion(
                id="attachments-messy",
                priority="medium",
                title=f"{len(attachments)} attachment(s) misplaced or orphaned",
                detail=", ".join(f.path for f in attachments[:5]),
                action="Co-locate with owning note's assets/ or archive orphans: deeporbit --vault . hygiene",
            )
        )
    return out
