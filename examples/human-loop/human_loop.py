#!/usr/bin/env python3
"""Device-local, JSON-only guard and diary preparation for DeepOrbit."""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
import uuid
from zoneinfo import ZoneInfo

VERSION = 1
START = "<!-- human-loop:user:start -->"
END = "<!-- human-loop:user:end -->"
MODES = ("morning", "evening", "weekly")
EMPTY = {"", "待填写", "未填写", "待反馈", "尚未收到反馈", "未记录", "空白",
         "暂无反馈", "请输入", "填写", "填写这里", "在此填写", "...", "…", "—", "-", "_",
         "pending", "awaiting", "not recorded", "fill in", "fill in here", "answer here"}


class LoopError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def host_id():
    """Hash a stable hardware/platform identifier; never emit the identifier."""
    if sys.platform == "darwin":
        result = subprocess.run(
            ["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice", "-a"],
            check=True, capture_output=True, timeout=10)
        identifier = plistlib.loads(result.stdout)[0].get("IOPlatformUUID", "")
    else:
        candidates = (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id"))
        identifier = next((p.read_text().strip() for p in candidates if p.exists()), "")
    if not identifier:
        raise LoopError("host_identity_unavailable")
    return "sha256:" + hashlib.sha256(
        ("deeporbit-human-loop-v1:" + identifier).encode()).hexdigest()


def read_json(path, code):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (OSError, UnicodeError, ValueError):
        raise LoopError(code) from None


def inside(vault, relative):
    """Reject absolute paths, escapes, and symlinks outside the configured vault."""
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise LoopError("unsafe_path")
    path = vault / relative
    if not path.resolve().is_relative_to(vault.resolve()):
        raise LoopError("unsafe_path")
    return path


def system_directory(core):
    """Resolve the logical system directory in schema-v2 and schema-v3 vaults."""
    directories = core.get("directories", {})
    if not isinstance(directories, dict):
        raise LoopError("vault_config_invalid")
    system = directories.get("system", "99_System")
    if isinstance(system, dict):
        system = system.get("path")
    if not isinstance(system, str) or not system:
        raise LoopError("vault_config_invalid")
    return system


def validate_schedule(schedule):
    """Keep the guard clock and the minute-resolution cron expression identical."""
    try:
        clock = schedule["time"]
        minutes = schedule["window_minutes"]
        weekdays = schedule["weekdays"]
        if not isinstance(clock, str) or not re.fullmatch(r"\d{2}:\d{2}", clock):
            raise ValueError()
        target = dt.time.fromisoformat(clock)
        if type(minutes) not in (int, float) or not 0 < minutes <= 180 or not math.isfinite(minutes):
            raise ValueError()
        if not isinstance(weekdays, list) or not weekdays or any(
                type(day) is not int or not 0 <= day <= 6 for day in weekdays):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise LoopError("schedule_invalid") from None
    return target, minutes, weekdays


def context(config_path, current_host=None):
    local = read_json(config_path, "local_config_unavailable")
    if local.get("schema_version") != VERSION:
        raise LoopError("local_schema_mismatch")
    try:
        vault = Path(local["vault_path"]).expanduser().resolve()
    except (KeyError, TypeError):
        raise LoopError("local_config_invalid") from None
    core = read_json(vault / "deeporbit.json", "vault_unavailable")
    if core.get("vault_id") != local.get("vault_id"):
        raise LoopError("vault_id_mismatch")
    system = system_directory(core)
    settings = read_json(inside(vault, system + "/DeepOrbit/human-loop.json"),
                         "shared_settings_unavailable")
    if settings.get("schema_version") != VERSION:
        raise LoopError("shared_schema_mismatch")
    if settings.get("vault_id") != local.get("vault_id"):
        raise LoopError("shared_vault_id_mismatch")
    try:
        zone = ZoneInfo(settings["timezone"])
        first = dt.date.fromisoformat(settings["trial"]["start"])
        last = dt.date.fromisoformat(settings["trial"]["end"])
        paths = settings["paths"]
        for key in ("daily_template", "daily_dir", "agent_dir"):
            inside(vault, paths[key])
        for relative in paths.values():
            inside(vault, relative)
        daily = inside(vault, paths["daily_dir"]).resolve()
        agent = inside(vault, paths["agent_dir"]).resolve()
        if agent == daily or any(re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", x)
                                 for x in agent.relative_to(vault).parts):
            raise LoopError("agent_directory_overlaps_daily")
        if any(x.endswith(".md") for x in agent.relative_to(vault).parts):
            raise LoopError("agent_directory_is_note")
        fields = settings["required_fields"]
        if first > last or not isinstance(fields, list) or len(fields) != 5:
            raise ValueError()
        if not all(isinstance(x, str) and x.endswith(("：", ":")) for x in fields):
            raise ValueError()
        if len(set(fields)) != 5:
            raise ValueError()
        for mode in MODES:
            validate_schedule(settings["schedule"][mode])
    except (KeyError, TypeError, ValueError):
        raise LoopError("shared_settings_invalid") from None
    return {"local": local, "vault": vault, "settings": settings,
            "zone": zone, "first": first, "last": last,
            "host_matches": local.get("host_id") == (current_host or host_id())}


def guard(ctx, mode, now=None, check_window=True, day=None):
    now = now or dt.datetime.now(ctx["zone"])
    now = now.astimezone(ctx["zone"])
    day = day or now.date()
    result = {"allowed": False, "reason": "disabled", "mode": mode,
              "date": day.isoformat(), "timezone": str(ctx["zone"])}
    if ctx["local"].get("role") != "primary":
        result["reason"] = "not_primary"
    elif not ctx["host_matches"]:
        result["reason"] = "host_mismatch"
    elif not ctx["local"].get("device_id") or ctx["local"]["device_id"] != ctx["settings"].get("scheduler_owner"):
        result["reason"] = "not_owner"
    elif ctx["settings"].get("enabled") is not True:
        pass
    elif not ctx["first"] <= day <= ctx["last"]:
        result["reason"] = "outside_trial"
    else:
        try:
            schedule = ctx["settings"]["schedule"][mode]
            target, minutes, weekdays = validate_schedule(schedule)
            start = dt.datetime.combine(day, target, ctx["zone"])
            stop = start + dt.timedelta(minutes=minutes)
        except (KeyError, TypeError, ValueError):
            raise LoopError("schedule_invalid") from None
        result["window"] = {"start": start.isoformat(), "end_exclusive": stop.isoformat()}
        if day.weekday() not in weekdays:
            result["reason"] = "wrong_weekday"
        elif check_window and not start <= now < stop:
            result["reason"] = "outside_window"
        else:
            result.update(allowed=True, reason="ok")
    return result


def substantive(value):
    value = value.strip().strip("。！!；; ")
    if value.casefold() in EMPTY or re.fullmatch(r"(?:\{\{.*?\}\}|<.*?>)", value):
        return False
    placeholder = re.fullmatch(r"\[([^\[\]]*)\]", value)
    if placeholder and placeholder.group(1).strip().casefold() in EMPTY:
        return False
    return bool(value)


def feedback(path, fields):
    result = {"state": "missing", "filled_count": 0, "missing_fields": list(fields),
              "explicit_user_state": None}
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return result
    except (OSError, UnicodeError):
        raise LoopError("daily_unreadable") from None
    result["state"] = "awaiting"
    if content.count(START) != 1 or content.count(END) != 1:
        result["reason"] = "malformed_user_block"
        return result
    block = content.split(START, 1)[1].split(END, 1)[0]
    if content.index(END) < content.index(START):
        result["reason"] = "malformed_user_block"
        return result
    values = {}
    current = None
    duplicates = False
    for line in block.splitlines():
        line = re.sub(r"^\s*-\s+", "", line).strip()
        if line.startswith("本人状态："):
            current = None
            state = line.removeprefix("本人状态：").strip()
            if state in ("待反馈", "完成", "部分", "休息"):
                result["explicit_user_state"] = state
            continue
        field = next((x for x in fields if line.startswith(x)), None)
        if field:
            duplicates |= field in values
            values[field] = line[len(field):].strip()
            current = field
        elif re.match(r"^#{1,6}\s", line):
            current = None
        elif current:
            values[current] += "\n" + line
    if duplicates:
        result["reason"] = "duplicate_user_fields"
        return result
    missing = [field for field in fields if not substantive(values.get(field, ""))]
    result.update(filled_count=len(fields) - len(missing), missing_fields=missing)
    result["state"] = "recorded" if not missing else ("partial" if len(missing) < 5 else "awaiting")
    return result


def daily_path(ctx, day):
    return inside(ctx["vault"], ctx["settings"]["paths"]["daily_dir"] + "/" + day.isoformat() + ".md")


def render_template(template, day, paths=None):
    """Change metadata only in the new copy; the template is never rewritten."""
    if not template.startswith("---\n") or "\n---\n" not in template[4:]:
        raise LoopError("template_frontmatter_invalid")
    front, body = template[4:].split("\n---\n", 1)
    keys = r"^(?:type|author|date|created|updated|privacy_level)\s*:"
    preserved = [line for line in front.splitlines() if not re.match(keys, line)]
    canonical = ["type: daily-feedback", "author: ai", "date: " + day.isoformat(),
                 "created: " + day.isoformat(), "updated: " + day.isoformat(),
                 "privacy_level: critical"]
    rendered = "---\n" + "\n".join(canonical + preserved) + "\n---\n" + body.lstrip("\n")
    rendered = rendered.replace("{{date}}", day.isoformat()).replace(
        "{{previous_date}}", (day - dt.timedelta(days=1)).isoformat()).replace(
        "{{weekday}}", "一二三四五六日"[day.weekday()])
    for key in ("daily_dir", "agent_dir"):
        if paths and key in paths:
            rendered = rendered.replace("{{" + key + "}}", paths[key])
    return rendered


def prepare(ctx, mode, now=None, dry_run=False, day=None):
    result = guard(ctx, mode, now, check_window=not dry_run, day=day)
    result.update(dry_run=dry_run, created=False)
    if not result["allowed"]:
        return result
    day = dt.date.fromisoformat(result["date"])
    paths = ctx["settings"]["paths"]
    path = daily_path(ctx, day)
    agent_relative = paths["agent_dir"] + "/" + day.isoformat() + "-" + mode + ".md"
    inside(ctx["vault"], agent_relative)
    result.update(vault_path=str(ctx["vault"]), daily_path=str(path.relative_to(ctx["vault"])),
                  agent_path=agent_relative,
                  reference_paths={k: v for k, v in paths.items()
                                   if k not in ("daily_template", "daily_dir", "agent_dir")})
    result["recent_days"] = [
        {"date": (day - dt.timedelta(days=n)).isoformat(),
         "path": str(daily_path(ctx, day - dt.timedelta(days=n)).relative_to(ctx["vault"])),
         "exists": daily_path(ctx, day - dt.timedelta(days=n)).is_file()}
        for n in range(6, -1, -1)]
    if mode == "morning" and not path.exists():
        try:
            template = inside(ctx["vault"], paths["daily_template"]).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            raise LoopError("template_unavailable") from None
        if template.count(START) != 1 or template.count(END) != 1:
            raise LoopError("template_user_block_invalid")
        rendered = render_template(template, day, paths)
        result["would_create"] = True
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
                    stream.write(rendered)
                    stream.flush()
                    os.fsync(stream.fileno())
                result["created"] = True
    result["feedback"] = feedback(path, ctx["settings"]["required_fields"])
    return result


def bind(vault, role, config_path=None):
    vault = Path(vault).expanduser().resolve()
    core = read_json(vault / "deeporbit.json", "vault_unavailable")
    vault_id = core.get("vault_id")
    if not isinstance(vault_id, str) or not re.fullmatch(r"[a-zA-Z0-9-]+", vault_id):
        raise LoopError("vault_id_invalid")
    path = Path(config_path) if config_path else Path.home() / ".config/deeporbit/human-loop" / (vault_id + ".json")
    if path.resolve().is_relative_to(vault):
        raise LoopError("local_config_must_be_outside_vault")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    value = {"schema_version": VERSION, "vault_id": vault_id, "vault_path": str(vault),
             "role": role, "host_id": host_id(), "device_id": str(uuid.uuid4())}
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise LoopError("local_config_exists") from None
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"config_path": str(path), "vault_id": vault_id, "role": role,
            "device_id": value["device_id"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Device-local configuration JSON; never sync it")
    subs = parser.add_subparsers(dest="command", required=True)
    binding = subs.add_parser("bind")
    binding.add_argument("--vault", required=True)
    binding.add_argument("--role", choices=("primary", "secondary"), required=True)
    subs.add_parser("status")
    for command in ("gate", "prepare"):
        child = subs.add_parser(command)
        child.add_argument("--mode", choices=MODES, required=True)
        if command == "prepare":
            child.add_argument("--dry-run", action="store_true")
            child.add_argument("--date", type=dt.date.fromisoformat)
    args = parser.parse_args()
    try:
        if args.command == "bind":
            result = bind(args.vault, args.role, args.config)
        else:
            if not args.config:
                raise LoopError("config_argument_required")
            ctx = context(args.config)
            if args.command == "status":
                day = dt.datetime.now(ctx["zone"]).date()
                result = {"vault_id": ctx["local"]["vault_id"], "date": day.isoformat(),
                          "enabled": ctx["settings"].get("enabled") is True,
                          "role": ctx["local"].get("role"), "host_matches": ctx["host_matches"],
                          "is_scheduler_owner": bool(ctx["local"].get("device_id")) and ctx["local"].get("device_id") == ctx["settings"].get("scheduler_owner"),
                          "in_trial": ctx["first"] <= day <= ctx["last"],
                          "feedback": feedback(daily_path(ctx, day), ctx["settings"]["required_fields"])}
            elif args.command == "gate":
                result = guard(ctx, args.mode)
            else:
                if args.date and not args.dry_run:
                    raise LoopError("date_override_requires_dry_run")
                result = prepare(ctx, args.mode, dry_run=args.dry_run, day=args.date)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("allowed", True) else 3
    except LoopError as error:
        print(json.dumps({"allowed": False, "error": error.code, "reason": error.code}))
        return 2
    except (OSError, subprocess.SubprocessError, ValueError):
        print(json.dumps({"allowed": False, "error": "runtime_unavailable", "reason": "runtime_unavailable"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
