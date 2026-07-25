from __future__ import annotations

import datetime as dt
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .errors import TaskNotFoundError

TASK_RE = re.compile(
    r"^(?P<indent>\s*)- \[(?P<mark>[ xX/\-])\]\s+(?P<body>.*?)(?:\s+\^do-(?P<id>[a-zA-Z0-9-]+))?\s*$"
)
DATE_FIELD_RE = re.compile(r"(?P<kind>[⏳📅➕✅❌])\s*(?P<date>\d{4}-\d{2}-\d{2})")
TIME_RE = re.compile(r"⏰\s*(?:(?P<date>\d{4}-\d{2}-\d{2})\s+)?(?P<time>\d{1,2}:\d{2})")
PRIORITY_MAP = {"🔺": "highest", "⏫": "high", "🔼": "medium", "🔽": "low", "⏬": "lowest"}
PRIORITY_EMOJI = {v: k for k, v in PRIORITY_MAP.items()}
RECURRENCE_RE = re.compile(r"🔁\s*(?P<rule>every\b[^⏳📅➕✅❌⏰🔺⏫🔼🔽⏬⛔^#]*?)(?=\s+[⏳📅➕✅❌⏰🔺⏫🔼🔽⏬⛔]|\s+\^|\s+#|\s*$)")
DEPENDS_RE = re.compile(r"⛔\s*(?P<ids>[a-zA-Z0-9\-, ]+?)(?=\s+[⏳📅➕✅❌⏰🔺⏫🔼🔽⏬🔁]|\s+\^|\s+#|\s*$)")
TAG_RE = re.compile(r"#(?P<tag>[A-Za-z0-9_一-鿿/\-]+)")
ATTACH_RE = re.compile(r"!\[\[(?P<target>[^\]]+)\]\]")
STATUS_OF_MARK = {" ": "todo", "x": "done", "X": "done", "/": "doing", "-": "cancelled"}
MARK_OF_STATUS = {"todo": " ", "done": "x", "doing": "/", "cancelled": "-"}
STATUSES = tuple(MARK_OF_STATUS)
DATE_EMOJI = {"scheduled": "⏳", "due": "📅", "created": "➕", "done_date": "✅", "cancelled_date": "❌"}


@dataclass(slots=True)
class Task:
    id: str
    text: str
    done: bool
    path: str
    line: int
    scheduled: str | None = None
    due: str | None = None
    status: str = "todo"
    indent: int = 0
    parent: str | None = None
    time: str | None = None
    priority: str | None = None
    recurrence: str | None = None
    created: str | None = None
    done_date: str | None = None
    cancelled_date: str | None = None
    depends: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)


def _new_id() -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{now}-{secrets.token_hex(3)}"


def _task_files(config: Config):
    for rel in config.index_dirs:
        root = config.vault / rel
        if root.is_dir():
            yield from root.rglob("*.md")


def _indent_level(raw: str) -> int:
    return len(raw.replace("\t", "  ")) // 2


def _strip_markers(body: str) -> str:
    text = DATE_FIELD_RE.sub(" ", body)
    text = TIME_RE.sub(" ", text)
    text = RECURRENCE_RE.sub(" ", text)
    text = DEPENDS_RE.sub(" ", text)
    for emoji in PRIORITY_MAP:
        text = text.replace(emoji, " ")
    return re.sub(r"\s+", " ", text).strip()


def _parse_body(body: str) -> dict:
    fields: dict = {"scheduled": None, "due": None, "created": None, "done_date": None, "cancelled_date": None}
    for match in DATE_FIELD_RE.finditer(body):
        kind = {"⏳": "scheduled", "📅": "due", "➕": "created", "✅": "done_date", "❌": "cancelled_date"}[match.group("kind")]
        fields[kind] = match.group("date")
    time_match = TIME_RE.search(body)
    fields["time"] = time_match.group("time") if time_match else None
    if time_match and time_match.group("date"):
        fields.setdefault("due", None)
        if fields["due"] is None:
            fields["due"] = time_match.group("date")
    fields["priority"] = next((PRIORITY_MAP[e] for e in PRIORITY_MAP if e in body), None)
    recur = RECURRENCE_RE.search(body)
    fields["recurrence"] = recur.group("rule").strip() if recur else None
    depends = DEPENDS_RE.search(body)
    fields["depends"] = [d.strip() for d in depends.group("ids").split(",") if d.strip()] if depends else []
    fields["tags"] = TAG_RE.findall(body)
    fields["attachments"] = ATTACH_RE.findall(body)
    fields["text"] = _strip_markers(body)
    return fields


def parse_tasks(config: Config) -> list[Task]:
    tasks: list[Task] = []
    for path in sorted(set(_task_files(config))):
        stack: list[Task] = []
        rel = path.relative_to(config.vault).as_posix()
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            match = TASK_RE.match(line)
            if not match:
                continue
            body = match.group("body")
            fields = _parse_body(body)
            status = STATUS_OF_MARK[match.group("mark")]
            indent = _indent_level(match.group("indent"))
            while stack and stack[-1].indent >= indent:
                stack.pop()
            task = Task(
                id=match.group("id") or f"legacy-{path.stem}-{line_no}",
                text=fields["text"],
                done=status == "done",
                path=rel,
                line=line_no,
                scheduled=fields["scheduled"],
                due=fields["due"],
                status=status,
                indent=indent,
                parent=stack[-1].id if stack else None,
                time=fields["time"],
                priority=fields["priority"],
                recurrence=fields["recurrence"],
                created=fields["created"],
                done_date=fields["done_date"],
                cancelled_date=fields["cancelled_date"],
                depends=fields["depends"],
                tags=fields["tags"],
                attachments=fields["attachments"],
            )
            tasks.append(task)
            stack.append(task)
    return tasks


def render_line(task: Task, *, mark: str | None = None) -> str:
    """Canonical one-line rendering; text keeps inline #tags and ![[attachments]]."""
    bits = [f"{'  ' * task.indent}- [{mark or MARK_OF_STATUS[task.status]}] {task.text.strip()}"]
    if task.priority and task.priority in PRIORITY_EMOJI:
        bits.append(PRIORITY_EMOJI[task.priority])
    if task.recurrence:
        bits.append(f"🔁 {task.recurrence}")
    if task.depends:
        bits.append(f"⛔ {','.join(task.depends)}")
    if task.scheduled:
        bits.append(f"⏳ {task.scheduled}")
    if task.due:
        bits.append(f"📅 {task.due}")
    if task.time:
        bits.append(f"⏰ {task.time}")
    if task.created:
        bits.append(f"➕ {task.created}")
    if task.done_date:
        bits.append(f"✅ {task.done_date}")
    if task.cancelled_date:
        bits.append(f"❌ {task.cancelled_date}")
    bits.append(f"^do-{task.id}")
    return " ".join(bits)


def _destination_path(config: Config, destination: str) -> Path:
    if destination == "today":
        return config.path("diary") / f"{dt.date.today().isoformat()}.md"
    if destination.startswith("project:"):
        return config.path("projects") / f"{destination.split(':', 1)[1]}.md"
    return config.path("inbox") / "Todos.md"


def add_task(
    config: Config,
    text: str,
    *,
    destination: str = "inbox",
    scheduled: str | None = None,
    due: str | None = None,
    time: str | None = None,
    priority: str | None = None,
    recurrence: str | None = None,
    depends: list[str] | None = None,
    parent_line: int | None = None,
) -> Task:
    path = _destination_path(config, destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Todos\n"
    if not existing.endswith("\n"):
        existing += "\n"
    indent = 0
    insert_at: int | None = None
    if parent_line is not None:
        lines = existing.splitlines()
        parent_match = TASK_RE.match(lines[parent_line - 1]) if 0 < parent_line <= len(lines) else None
        if parent_match is None:
            raise TaskNotFoundError(f"Parent task line not found: {parent_line}")
        indent = _indent_level(parent_match.group("indent")) + 1
        insert_at = parent_line
        for i in range(parent_line, len(lines)):
            child = TASK_RE.match(lines[i])
            if child and _indent_level(child.group("indent")) >= indent:
                insert_at = i + 1
            elif child:
                break
    body = text.strip()
    if indent == 0 and "#task" not in body:
        body = f"{body} #task"
    task = Task(
        id=_new_id(),
        text=body,
        done=False,
        path=path.relative_to(config.vault).as_posix(),
        line=0,
        scheduled=scheduled,
        due=due,
        time=time,
        priority=priority,
        recurrence=recurrence,
        created=dt.date.today().isoformat(),
        depends=depends or [],
        indent=indent,
    )
    line = render_line(task)
    if insert_at is None:
        path.write_text(existing + line + "\n", encoding="utf-8")
        task.line = len(existing.splitlines()) + 1
    else:
        lines = existing.splitlines()
        lines.insert(insert_at, line)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        task.line = insert_at + 1
    return task


def _rewrite_line(config: Config, task: Task, new_line: str) -> None:
    path = config.vault / task.path
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[task.line - 1] = new_line
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find(config: Config, task_id: str) -> Task:
    for task in parse_tasks(config):
        if task.id == task_id:
            return task
    raise TaskNotFoundError(f"Task not found: {task_id}")


def update_task(config: Config, task_id: str, **updates) -> Task:
    """Rewrite one task line with new field values (status/due/time/priority/recurrence/depends/text)."""
    task = _find(config, task_id)
    for key, value in updates.items():
        if not hasattr(task, key):
            raise ValueError(f"Unknown task field: {key}")
        setattr(task, key, value)
    if task.status == "done":
        task.done = True
        if not task.done_date:
            task.done_date = dt.date.today().isoformat()
    _rewrite_line(config, task, render_line(task))
    return task


def complete_task(config: Config, task_id: str) -> Task:
    task = _find(config, task_id)
    return update_task(config, task_id, status="done", done=True, done_date=task.done_date or dt.date.today().isoformat())


def progress(tasks: list[Task]) -> dict[str, dict]:
    """Per-parent subtask counts plus per-project (via #project/* tag) completion stats."""
    children: dict[str, list[Task]] = {}
    for task in tasks:
        if task.parent:
            children.setdefault(task.parent, []).append(task)
    subtasks = {
        parent: {"done": sum(1 for c in kids if c.done), "total": len(kids)}
        for parent, kids in children.items()
    }
    projects: dict[str, dict] = {}
    for task in tasks:
        if task.parent:
            continue
        for tag in task.tags:
            if not tag.startswith("project/"):
                continue
            bucket = projects.setdefault(tag.split("/", 1)[1], {"done": 0, "total": 0})
            bucket["total"] += 1
            bucket["done"] += 1 if task.done else 0
    return {"subtasks": subtasks, "projects": projects}


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
