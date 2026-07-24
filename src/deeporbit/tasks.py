from __future__ import annotations

import datetime as dt
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .errors import TaskNotFoundError

TASK_RE = re.compile(r"^(?P<prefix>\s*- \[(?P<done>[ xX])\]\s+)(?P<body>.*?)(?:\s+\^do-(?P<id>[a-zA-Z0-9-]+))?\s*$")
DATE_RE = re.compile(r"(?P<kind>[⏳📅])\s*(?P<date>\d{4}-\d{2}-\d{2})")


@dataclass(slots=True)
class Task:
    id: str
    text: str
    done: bool
    path: str
    line: int
    scheduled: str | None = None
    due: str | None = None


def _new_id() -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{now}-{secrets.token_hex(3)}"


def _task_files(config: Config):
    for rel in config.index_dirs:
        root = config.vault / rel
        if root.is_dir():
            yield from root.rglob("*.md")


def parse_tasks(config: Config) -> list[Task]:
    tasks: list[Task] = []
    for path in sorted(set(_task_files(config))):
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            match = TASK_RE.match(line)
            if not match:
                continue
            scheduled = due = None
            for date_match in DATE_RE.finditer(match.group("body")):
                if date_match.group("kind") == "⏳":
                    scheduled = date_match.group("date")
                else:
                    due = date_match.group("date")
            tasks.append(Task(match.group("id") or f"legacy-{path.stem}-{line_no}", match.group("body"), match.group("done").lower() == "x", path.relative_to(config.vault).as_posix(), line_no, scheduled, due))
    return tasks


def add_task(config: Config, text: str, *, destination: str = "inbox", scheduled: str | None = None, due: str | None = None) -> Task:
    if destination == "today":
        path = config.vault / "10_Diary" / f"{dt.date.today().isoformat()}.md"
    elif destination.startswith("project:"):
        path = config.vault / "20_Projects" / f"{destination.split(':', 1)[1]}.md"
    else:
        path = config.vault / "00_Inbox" / "Todos.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    task_id = _new_id()
    bits = [f"- [ ] {text.strip()} #task"]
    if scheduled:
        bits.append(f"⏳ {scheduled}")
    if due:
        bits.append(f"📅 {due}")
    bits.append(f"^do-{task_id}")
    line = " ".join(bits)
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Todos\n"
    if not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + line + "\n", encoding="utf-8")
    return Task(task_id, " ".join(bits[0:-1])[6:], False, path.relative_to(config.vault).as_posix(), len(existing.splitlines()) + 1, scheduled, due)


def complete_task(config: Config, task_id: str) -> Task:
    for task in parse_tasks(config):
        if task.id != task_id:
            continue
        path = config.vault / task.path
        lines = path.read_text(encoding="utf-8").splitlines()
        lines[task.line - 1] = re.sub(r"^(\s*- )\[ \]", r"\1[x]", lines[task.line - 1], count=1)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        task.done = True
        return task
    raise TaskNotFoundError(f"Task not found: {task_id}")


def agenda(config: Config, *, today: dt.date | None = None) -> dict[str, list[Task]]:
    today = today or dt.date.today()
    groups: dict[str, list[Task]] = {"overdue": [], "today": [], "upcoming": [], "unscheduled": [], "done": []}
    for task in parse_tasks(config):
        if task.done:
            groups["done"].append(task)
            continue
        target = task.due or task.scheduled
        if not target:
            groups["unscheduled"].append(task)
        else:
            date = dt.date.fromisoformat(target)
            groups["overdue" if date < today else "today" if date == today else "upcoming"].append(task)
    return groups
