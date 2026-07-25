"""Due-task reminders: deterministic due check, local notification delivery.

Scheduling lives in launchd (see `install`); this module owns the check and
the delivery. Delivery prefers the optional `alerter` binary (interactive
[完成]/[稍后] actions) and falls back to a zero-dependency `osascript`
banner. State in ~/.config/deeporbit/reminders.json keeps delivery
idempotent and carries snooze records.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import xml.sax.saxutils
from pathlib import Path

from .config import Config
from .tasks import Task, complete_task, parse_tasks

STATE_NAME = "reminders.json"
SNOOZE_MINUTES = 10
PLIST_LABEL = "com.deeporbit.remind"


def state_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "deeporbit" / STATE_NAME


def _load_state() -> dict:
    path = state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}  # corrupt state file: treat as empty, never crash
    return data if isinstance(data, dict) else {}


def _save_state(state: dict) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mark_reminded(task_id: str, when: dt.datetime | None = None) -> None:
    when = when or dt.datetime.now()
    state = _load_state()
    entry = state.setdefault(task_id, {})
    entry["reminded_at"] = when.isoformat(timespec="seconds")
    entry.pop("snooze_until", None)
    _save_state(state)


def snooze(task_id: str, minutes: int = SNOOZE_MINUTES, now: dt.datetime | None = None) -> dt.datetime:
    now = now or dt.datetime.now()
    until = now + dt.timedelta(minutes=minutes)
    state = _load_state()
    entry = state.setdefault(task_id, {})
    entry["reminded_at"] = now.isoformat(timespec="seconds")
    entry["snooze_until"] = until.isoformat(timespec="seconds")
    _save_state(state)
    return until


def check(config: Config, now: dt.datetime | None = None) -> list[Task]:
    """Open tasks whose due date arrived (and ⏰ time passed) and not yet reminded."""
    now = now or dt.datetime.now()
    today = now.date()
    state = _load_state()
    due: list[Task] = []
    for task in parse_tasks(config):
        if task.status not in ("todo", "doing") or not task.due:
            continue
        try:
            due_date = dt.date.fromisoformat(task.due)
        except ValueError:
            continue
        if due_date > today:
            continue
        if task.time and due_date == today:
            try:
                clock = dt.time.fromisoformat(task.time)
            except ValueError:
                continue
            if (clock.hour, clock.minute) > (now.hour, now.minute):
                continue
        entry = state.get(task.id) or {}
        snooze_until = entry.get("snooze_until")
        if snooze_until:
            try:
                if dt.datetime.fromisoformat(snooze_until) > now:
                    continue  # still snoozed
            except ValueError:
                pass
            due.append(task)  # snooze expired: remind again
        elif entry.get("reminded_at"):
            continue  # already delivered, stay idempotent
        else:
            due.append(task)
    return due


def _applescript_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def deliver(config: Config, task: Task) -> dict:
    """Deliver one reminder; returns {task_id, channel, action, ...}."""
    alerter = shutil.which("alerter")
    if alerter:
        payload: dict = {}
        try:
            proc = subprocess.run(
                [alerter, "-title", "DeepOrbit 提醒", "-message", task.text,
                 "-actions", "完成,稍后", "-json"],
                capture_output=True, text=True, timeout=30,
            )
            payload = json.loads(proc.stdout or "{}")
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            payload = {}
        choice = payload.get("activationValue") or ""
        if choice == "完成":
            complete_task(config, task.id)
            action = "done"
        elif choice == "稍后":
            until = snooze(task.id, SNOOZE_MINUTES)
            action = "snoozed"
        else:
            mark_reminded(task.id)
            action = "notified"
        result = {"task_id": task.id, "channel": "alerter", "action": action}
        if action == "snoozed":
            result["snooze_until"] = until.isoformat(timespec="seconds")
        return result
    script = f'display notification "{_applescript_escape(task.text)}" with title "DeepOrbit 提醒"'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        pass
    mark_reminded(task.id)
    return {"task_id": task.id, "channel": "osascript", "action": "notified"}


def _plist(program_arguments: list[str]) -> str:
    args = "\n".join(f"    <string>{xml.sax.saxutils.escape(arg)}</string>" for arg in program_arguments)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n<dict>\n'
        f"  <key>Label</key>\n  <string>{PLIST_LABEL}</string>\n"
        "  <key>ProgramArguments</key>\n  <array>\n"
        f"{args}\n"
        "  </array>\n"
        "  <key>StartInterval</key>\n  <integer>60</integer>\n"
        "  <key>RunAtLoad</key>\n  <true/>\n"
        "</dict>\n</plist>\n"
    )


def install(config: Config, *, base_dir: Path | None = None) -> dict:
    """Write the launchd agent for minute-polling reminders and try to load it.

    Never raises: write or launchctl failures come back as manual guidance.
    """
    deeporbit = shutil.which("deeporbit")
    program_arguments = (
        [deeporbit] if deeporbit else [sys.executable, "-m", "deeporbit"]
    ) + ["--vault", str(config.vault), "remind", "check", "--deliver"]
    launch_agents = base_dir or (Path.home() / "Library" / "LaunchAgents")
    plist_path = launch_agents / f"{PLIST_LABEL}.plist"
    result: dict = {
        "plist": str(plist_path),
        "program_arguments": program_arguments,
        "start_interval": 60,
        "uninstall": f"launchctl unload -w {plist_path} && rm {plist_path}",
    }
    try:
        launch_agents.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(_plist(program_arguments), encoding="utf-8")
    except OSError as exc:
        result.update({
            "installed": False,
            "loaded": False,
            "error": str(exc),
            "manual": (
                f"无法写入 {plist_path}（{exc}）。请手动创建该文件，内容为标准 launchd plist："
                f"Label={PLIST_LABEL}，StartInterval=60，ProgramArguments={program_arguments}，"
                f"然后执行 launchctl load -w {plist_path}"
            ),
        })
        return result
    result["installed"] = True
    try:
        proc = subprocess.run(
            ["launchctl", "load", "-w", str(plist_path)],
            capture_output=True, text=True, timeout=30,
        )
        result["loaded"] = proc.returncode == 0
        if proc.returncode != 0:
            result["manual"] = (
                f"plist 已写入但 launchctl 加载失败：{proc.stderr.strip() or proc.stdout.strip()}。"
                f"请手动执行 launchctl load -w {plist_path}"
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["loaded"] = False
        result["manual"] = f"plist 已写入；请手动执行 launchctl load -w {plist_path}（{exc}）"
    return result
