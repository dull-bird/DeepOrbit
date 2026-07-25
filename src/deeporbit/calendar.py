from __future__ import annotations

import datetime as dt
from pathlib import Path

from .config import Config
from .errors import PrivacyError
from .privacy import sanitize_value
from .privacy_scanner import effective_mode as privacy_effective_mode, file_level
from .tasks import parse_tasks


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def export_ics(config: Config, output: Path | None = None, *, privacy_mode: str | None = None) -> tuple[Path, int]:
    output = output or config.vault / "99_System" / "Calendar" / "DeepOrbit.ics"
    output.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//DeepOrbit//Tasks//EN", "CALSCALE:GREGORIAN"]
    count = 0
    for task in parse_tasks(config):
        date = task.due or task.scheduled
        if task.done or not date:
            continue
        task_path = config.vault / task.path
        level = file_level(task_path) if task_path.exists() else "low"
        command_mode = privacy_mode or config.privacy.get("outbound_mode", "allow")
        mode = privacy_effective_mode(level, command_mode)
        if mode == "block":
            raise PrivacyError(f"Outbound privacy block for task from {task.path}")
        compact = date.replace("-", "")
        summary = re_clean_task(task.text)
        summary = sanitize_value(
            summary,
            mode=mode,
            rules=config.privacy.get("rules"),
        ).value
        description = task.path if mode == "allow" else "<VAULT_PATH>"
        if task.time:
            # Timed event: floating local time, one-hour block, 10-minute alert.
            start = dt.datetime.combine(dt.date.fromisoformat(date), dt.time.fromisoformat(task.time))
            dtstart = f"DTSTART;VALUE=DATE-TIME:{start.strftime('%Y%m%dT%H%M%S')}"
            dtend = f"DTEND;VALUE=DATE-TIME:{(start + dt.timedelta(hours=1)).strftime('%Y%m%dT%H%M%S')}"
            trigger = "TRIGGER;RELATED=START:-PT10M"
        else:
            dtstart = f"DTSTART;VALUE=DATE:{compact}"
            dtend = f"DTEND;VALUE=DATE:{(dt.date.fromisoformat(date) + dt.timedelta(days=1)).strftime('%Y%m%d')}"
            trigger = "TRIGGER;RELATED=START:PT9H"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{task.id}@deeporbit.local",
            f"DTSTAMP:{now}",
            dtstart,
            dtend,
            f"SUMMARY:{_escape(summary)}",
            f"DESCRIPTION:{_escape(description)}",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            trigger,
            f"DESCRIPTION:{_escape(summary)}",
            "END:VALARM",
            "END:VEVENT",
        ])
        count += 1
    lines.append("END:VCALENDAR")
    output.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return output, count


def re_clean_task(text: str) -> str:
    import re

    text = re.sub(r"\s+#task\b", "", text)
    text = re.sub(r"\s+[⏳📅]\s*\d{4}-\d{2}-\d{2}", "", text)
    text = re.sub(r"\s*!\[\[[^\]]+\]\]", "", text)  # attachments don't belong in calendar summaries
    text = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", text)  # [[target|alias]] → alias
    text = re.sub(r"\[\[([^\]]+)\]\]", lambda m: m.group(1).rsplit("/", 1)[-1], text)  # [[path/Note]] → Note
    return re.sub(r"\s+", " ", text).strip()
