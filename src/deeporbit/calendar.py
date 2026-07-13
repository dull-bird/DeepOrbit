from __future__ import annotations

import datetime as dt
from pathlib import Path

from .config import Config
from .tasks import parse_tasks


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def export_ics(config: Config, output: Path | None = None) -> tuple[Path, int]:
    output = output or config.vault / "99_System" / "Calendar" / "DeepOrbit.ics"
    output.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//DeepOrbit//Tasks//EN", "CALSCALE:GREGORIAN"]
    count = 0
    for task in parse_tasks(config):
        date = task.due or task.scheduled
        if task.done or not date:
            continue
        compact = date.replace("-", "")
        summary = re_clean_task(task.text)
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{task.id}@deeporbit.local",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{compact}",
            f"DTEND;VALUE=DATE:{(dt.date.fromisoformat(date) + dt.timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{_escape(summary)}",
            f"DESCRIPTION:{_escape(task.path)}",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "TRIGGER;RELATED=START:PT9H",
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
    return text.strip()
