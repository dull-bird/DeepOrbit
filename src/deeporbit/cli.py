from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from . import nltime
from .config import load_config
from .doctor import diagnose
from .errors import DeepOrbitError, TaskNotFoundError
from .frontmatter import write_fields
from .links import add_link, describe_link, list_links, remove_link, resolve_vault, route_link, set_default
from .profile import observe as profile_observe
from .profile import compact as profile_compact
from .profile import set_field as profile_set_field
from .profile import set_focus as profile_set_focus
from .profile import show as profile_show
from .privacy_scanner import DEFAULT_THRESHOLDS, LEVELS, PRIVACY_CATEGORIES, scan_file, scan_vault
from .calendar import export_ics
from .cron import add_job, list_jobs, remove_job, run_due, set_enabled
from .git_sync import sync_vault
from .hygiene import scan_hygiene
from .recipes import list_recipes, run_plan
from .openers import open_note
from .repolink import write_pointer
from .work import archive as work_archive
from .work import overview as work_overview
from .work import set_status as work_set_status
from .work import sweep as work_sweep
from .work import trash as work_trash
from .schema import build_schema
from .search import SearchIndex
from .semantic import ChromaIndex
from .suggest import suggest as build_suggestions
from .tasks import _destination_path, add_task, agenda, complete_task, parse_tasks, progress, update_task
from .vault import initialize


def _print(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="deeporbit")
    root.add_argument("--vault", default=".", help="Obsidian vault path")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--source", help="DeepOrbit repository checkout to materialize into the vault")
    commands.add_parser("doctor")
    link = commands.add_parser("link", help="Register and resolve external DeepOrbit vaults")
    link_sub = link.add_subparsers(dest="link_command", required=True)
    link_add = link_sub.add_parser("add", help="Register a vault path under a name")
    link_add.add_argument("name")
    link_add.add_argument("path")
    link_add.add_argument("--description", default="", help="What this vault is for; used to route requests")
    link_add.add_argument("--source", default="", help="Description author: user or agent")
    link_sub.add_parser("list", help="Show registered vaults")
    link_route = link_sub.add_parser("route", help="Pick the best vault for a natural-language request")
    link_route.add_argument("query")
    link_remove = link_sub.add_parser("remove", help="Unregister a vault")
    link_remove.add_argument("name")
    link_describe = link_sub.add_parser("describe", help="Set or refine a vault's purpose description")
    link_describe.add_argument("name")
    link_describe.add_argument("description")
    link_describe.add_argument("--source", default="user", choices=["user", "agent"])
    link_default = link_sub.add_parser("default", help="Set or show the default link")
    link_default.add_argument("name", nargs="?")
    open_cmd = commands.add_parser("open", help="Open a note through Obsidian CLI, URI, or path fallback")
    open_cmd.add_argument("path")
    open_cmd.add_argument("--dry-run", action="store_true", help="Resolve the preferred opener without launching it")
    index = commands.add_parser("index")
    index.add_argument("action", nargs="?", choices=["ensure", "status"], default="ensure")
    index.add_argument("--semantic", action="store_true", help="Also update optional Chroma semantic index")
    rag = commands.add_parser("rag")
    rag.add_argument("query")
    rag.add_argument("--limit", type=int, default=10)
    rag.add_argument("--semantic", action="store_true", help="Use optional semantic retrieval")
    todo = commands.add_parser("todo")
    todo_sub = todo.add_subparsers(dest="todo_command", required=True)
    add = todo_sub.add_parser("add")
    add.add_argument("text")
    add.add_argument("--today", action="store_true")
    add.add_argument("--project")
    add.add_argument("--scheduled")
    add.add_argument("--due")
    add.add_argument("--time", help="Reminder clock time HH:MM (⏰)")
    add.add_argument("--priority", choices=["highest", "high", "medium", "low", "lowest"])
    add.add_argument("--recur", help="Recurrence rule, e.g. 'every week on Friday' (🔁)")
    add.add_argument("--parent", help="Parent task line number or ^do-* block ID")
    list_cmd = todo_sub.add_parser("list")
    list_cmd.add_argument("--view", choices=["flat", "board", "timeline", "progress"], default="flat")
    list_cmd.add_argument("--md", action="store_true", help="Render Markdown tables instead of JSON")
    done = todo_sub.add_parser("done")
    done.add_argument("id")
    set_cmd = todo_sub.add_parser("set", help="Update fields of an existing task")
    set_cmd.add_argument("id")
    set_cmd.add_argument("--status", choices=["todo", "doing", "done", "cancelled"])
    set_cmd.add_argument("--due")
    set_cmd.add_argument("--time")
    set_cmd.add_argument("--priority", choices=["highest", "high", "medium", "low", "lowest"])
    set_cmd.add_argument("--recur", help="Recurrence rule (🔁)")
    attach = todo_sub.add_parser("attach", help="Copy a file into 90_Attachments and link it on the task")
    attach.add_argument("id")
    attach.add_argument("file")
    commands.add_parser("agenda")
    commands.add_parser("status", help="Overview of every work item by lifecycle status")
    commands.add_parser("suggest", help="Prioritized suggestions from vault state")
    sweep_cmd = commands.add_parser("sweep", help="Auto-pause active items idle for more than --days days")
    sweep_cmd.add_argument("--days", type=int, default=60)
    sweep_cmd.add_argument("--dry-run", action="store_true")
    cron = commands.add_parser("cron", help="Schedule recurring DeepOrbit workflows")
    cron_sub = cron.add_subparsers(dest="cron_command", required=True)
    cron_add = cron_sub.add_parser("add")
    cron_add.add_argument("name")
    cron_add.add_argument("instruction")
    cron_schedule = cron_add.add_mutually_exclusive_group()
    cron_schedule.add_argument("--every", default=None, help="hourly | daily | weekly | <N>h | <N>d (default: daily)")
    cron_schedule.add_argument("--at", default=None, help="One-shot ISO date/datetime, e.g. 2026-07-25T19:00")
    cron_sub.add_parser("list")
    cron_remove = cron_sub.add_parser("remove")
    cron_remove.add_argument("name")
    cron_sub.add_parser("run-due", help="Report jobs whose interval elapsed and stamp their last run")
    cron_rundue = cron_sub.choices["run-due"] if hasattr(cron_sub, "choices") else None
    if cron_rundue is not None:
        cron_rundue.add_argument("--agent", action="store_true", help="Wrap each due job in a ready-to-run agent CLI handoff")
    for toggle in ("enable", "disable"):
        toggle_cmd = cron_sub.add_parser(toggle)
        toggle_cmd.add_argument("name")
    remind = commands.add_parser("remind", help="Check and deliver due-task reminders (launchd-driven)")
    remind_sub = remind.add_subparsers(dest="remind_command", required=True)
    remind_check = remind_sub.add_parser("check", help="List due reminders as JSON")
    remind_check.add_argument("--deliver", action="store_true", help="Actually deliver notifications (alerter/osascript)")
    remind_sub.add_parser("install", help="Install the launchd agent for minute-polling reminders")
    recipe = commands.add_parser("recipe", help="List and resolve composable workflow recipes")
    recipe_sub = recipe.add_subparsers(dest="recipe_command", required=True)
    recipe_sub.add_parser("list")
    recipe_run = recipe_sub.add_parser("run", help="Resolve a recipe into an execution plan (JSON)")
    recipe_run.add_argument("name")
    commands.add_parser("hygiene", help="Detect attachment and code-file violations")
    sync = commands.add_parser("sync", help="Synchronize the vault with Git")
    sync.add_argument("--no-pull", action="store_true", help="Skip git pull before committing")
    sync.add_argument("--no-push", action="store_true", help="Skip git push after committing")
    sync.add_argument("--message", default="", help="Override the generated commit message")
    repo_link = commands.add_parser("repo-link", help="Write a canonical external-repo pointer note")
    repo_link.add_argument("repo")
    repo_link.add_argument("--at", required=True, help="Vault-relative pointer note path (.md)")
    repo_link.add_argument("--title", default="代码仓库")
    repo_link.add_argument("--github", default="")
    for verb, help_text in [
        ("pause", "Mark a note as paused"),
        ("resume", "Return a paused note to active"),
        ("done", "Mark a note as done"),
        ("archive", "Archive a note or project folder into 99_System/Archive"),
        ("trash", "Move a path into .trash (safe deletion)"),
    ]:
        command = commands.add_parser(verb, help=help_text)
        command.add_argument("path")
    profile = commands.add_parser("profile", help="Show and maintain the user profile")
    profile_sub = profile.add_subparsers(dest="profile_command", required=True)
    profile_sub.add_parser("show")
    profile_set = profile_sub.add_parser("set")
    profile_set.add_argument("key")
    profile_set.add_argument("value")
    profile_observe = profile_sub.add_parser("observe")
    profile_observe.add_argument("text")
    profile_observe.add_argument("--source", default="agent", choices=["agent", "user"])
    profile_focus = profile_sub.add_parser("focus", help="Replace the Focus section with a distilled identity summary")
    profile_focus.add_argument("text")
    profile_sub.add_parser("compact", help="Archive raw observations after distillation")
    calendar = commands.add_parser("calendar")
    calendar.add_argument("action", choices=["export"])
    calendar.add_argument("--output", type=Path)
    calendar.add_argument("--privacy-mode", choices=["allow", "redact", "block"], default=None)
    serve_cmd = commands.add_parser("serve", help="Open the local web dashboard (127.0.0.1 only)")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8765)
    serve_cmd.add_argument("--open", action="store_true", help="Open the dashboard in a browser")
    serve_cmd.add_argument("--agent", default="auto", help="ACP agent command (auto tries omp, claude, gemini)")
    serve_cmd.add_argument("--privacy-mode", choices=["allow", "redact", "block"], default=None)
    privacy = commands.add_parser("privacy", help="Privacy scanning and enforcement")
    privacy_sub = privacy.add_subparsers(dest="privacy_command", required=True)
    privacy_scan = privacy_sub.add_parser("scan", help="Scan vault notes for privacy risk")
    privacy_scan.add_argument("--min-level", choices=["low", "medium", "high", "critical"], default="low")
    privacy_scan.add_argument("--tag", action="store_true", help="Write privacy_level frontmatter")
    privacy_scan.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    privacy_scan.add_argument("--explain", action="store_true", help="Show per-file scoring layer breakdown")
    privacy_verify = privacy_sub.add_parser("verify", help="Collect gray-zone files with excerpts for LLM review")
    privacy_verify.add_argument("--max-chars", type=int, default=800, help="Max excerpt chars per file")
    privacy_apply = privacy_sub.add_parser("apply", help="Batch-apply privacy levels from a JSON decisions file")
    privacy_apply.add_argument("decisions", help="Path to JSON file: [{\"path\": ..., \"level\": ...}]")
    privacy_apply.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    teach_me = commands.add_parser("teach-me", help="Export vault knowledge into a Teach Me vault")
    teach_me_sub = teach_me.add_subparsers(dest="teach_me_command", required=True)
    teach_me_export = teach_me_sub.add_parser("export", help="Stage knowledge notes and run teach_me.py import")
    teach_me_export.add_argument("--script", default=None, help="Path to teach_me.py (or set TEACH_ME_SCRIPT)")
    teach_me_export.add_argument("--user", default=None, help="Teach Me user id")
    teach_me_export.add_argument(
        "--dirs",
        nargs="+",
        default=None,
        help="Vault dirs to export (default: 40_Wiki 60_Notes 30_Research)",
    )
    teach_me_export.add_argument("--timeout", type=float, default=120.0)
    agent = commands.add_parser("agent", help="Detect and configure the local agent CLI")
    agent_sub = agent.add_subparsers(dest="agent_command", required=True)
    agent_detect = agent_sub.add_parser("detect", help="Probe installed agent CLIs and their modes")
    agent_detect.add_argument("--versions", action="store_true", help="Also probe --version (slower)")
    agent_sub.add_parser("status", help="Show the configured agent and live detection")
    agent_configure = agent_sub.add_parser("configure", help="Choose the agent CLI and mode")
    agent_configure.add_argument("name", help="Agent name (omp, claude, gemini, codex)")
    agent_configure.add_argument("--mode", choices=["acp", "rpc", "print"], default=None)
    agent_sub.add_parser("clear", help="Remove the agent configuration")
    return root



def _link_dict(link) -> dict:
    payload = asdict(link)
    payload["path"] = str(link.path)
    return payload


def _task_date(task) -> str | None:
    return task.due or task.scheduled


def _timeline(tasks) -> dict:
    today = dt.date.today().isoformat()
    groups: dict = {"overdue": [], "today": [], "upcoming": {}, "unscheduled": []}
    for task in tasks:
        if task.done:
            continue
        date = _task_date(task)
        if not date:
            groups["unscheduled"].append(task)
        elif date < today:
            groups["overdue"].append(task)
        elif date == today:
            groups["today"].append(task)
        else:
            groups["upcoming"].setdefault(date, []).append(task)
    return groups


def _view_payload(tasks, view: str):
    if view == "board":
        return {status: [asdict(t) for t in tasks if t.status == status] for status in ("todo", "doing", "done", "cancelled")}
    if view == "timeline":
        groups = _timeline(tasks)
        return {
            "overdue": [asdict(t) for t in groups["overdue"]],
            "today": [asdict(t) for t in groups["today"]],
            "upcoming": {date: [asdict(t) for t in items] for date, items in sorted(groups["upcoming"].items())},
            "unscheduled": [asdict(t) for t in groups["unscheduled"]],
        }
    if view == "progress":
        return progress(tasks)
    return [asdict(t) for t in tasks]


def _md_cell(value) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _md_task_table(tasks) -> list[str]:
    lines = ["| ID | 状态 | 内容 | 截止 | 时间 | 优先级 |", "| --- | --- | --- | --- | --- | --- |"]
    for task in tasks:
        lines.append(
            "| " + " | ".join([
                _md_cell(task.id),
                _md_cell(task.status),
                _md_cell(task.text),
                _md_cell(_task_date(task)),
                _md_cell(task.time),
                _md_cell(task.priority),
            ]) + " |"
        )
    return lines


def _render_tasks_md(tasks, view: str) -> str:
    if view == "board":
        lines: list[str] = []
        for status in ("todo", "doing", "done", "cancelled"):
            group = [t for t in tasks if t.status == status]
            if group:
                lines += [f"## {status}", ""] + _md_task_table(group) + [""]
        return "\n".join(lines).strip()
    if view == "timeline":
        groups = _timeline(tasks)
        lines = []
        for title, items in [("Overdue", groups["overdue"]), ("Today", groups["today"])]:
            if items:
                lines += [f"## {title}", ""] + _md_task_table(items) + [""]
        for date, items in sorted(groups["upcoming"].items()):
            lines += [f"## {date}", ""] + _md_task_table(items) + [""]
        if groups["unscheduled"]:
            lines += ["## 未排期", ""] + _md_task_table(groups["unscheduled"]) + [""]
        return "\n".join(lines).strip()
    if view == "progress":
        stats = progress(tasks)
        lines = ["## 项目进度", "", "| 项目 | 完成 | 总数 | 进度 |", "| --- | --- | --- | --- |"]
        for name, bucket in sorted(stats["projects"].items()):
            total = bucket["total"]
            pct = f"{round(bucket['done'] / total * 100)}%" if total else "-"
            lines.append(f"| {_md_cell(name)} | {bucket['done']} | {total} | {pct} |")
        if stats["subtasks"]:
            by_id = {t.id: t for t in tasks}
            lines += ["", "## 子任务进度", "", "| 任务 | 进度 |", "| --- | --- |"]
            for parent, bucket in sorted(stats["subtasks"].items()):
                label = by_id[parent].text if parent in by_id else parent
                lines.append(f"| {_md_cell(label)} | [{bucket['done']}/{bucket['total']}] |")
        return "\n".join(lines)
    return "\n".join(_md_task_table(tasks))


def run(args: argparse.Namespace) -> int:
    if args.command == "link":
        if args.link_command == "add":
            _print(_link_dict(add_link(args.name, args.path, description=args.description, source=args.source)))
        elif args.link_command == "remove":
            _print(_link_dict(remove_link(args.name)))
        elif args.link_command == "describe":
            _print(_link_dict(describe_link(args.name, args.description, source=args.source)))
        elif args.link_command == "route":
            _print(route_link(args.query))
        elif args.link_command == "default":
            if args.name:
                _print(_link_dict(set_default(args.name)))
            else:
                _print([_link_dict(link) for link in list_links() if link.is_default])
        else:
            _print([_link_dict(link) for link in list_links()])
        return 0
    vault = resolve_vault(args.vault)
    if args.command == "init":
        result = initialize(vault, repo_source=args.source)
        _print(asdict(result))
        return 2 if result.conflicts else 0
    config = load_config(vault, create=False)
    if args.command == "open":
        candidate = Path(args.path)
        if not candidate.is_absolute():
            candidate = config.vault / candidate
        _print(open_note(candidate, execute=not args.dry_run))
    elif args.command == "doctor":
        _print(diagnose(config))
    elif args.command == "index":
        index = SearchIndex(config)
        if args.action == "status":
            status = index.status()
            status["semantic_available"] = ChromaIndex.available()
            _print(status)
        else:
            lexical = asdict(index.ensure())
            output = {"lexical": lexical}
            if args.semantic:
                output["semantic"] = asdict(ChromaIndex(config).ensure(index.file_manifest()))
            _print(output)
    elif args.command == "rag":
        index = SearchIndex(config)
        lexical = index.query(args.query, limit=args.limit)
        if args.semantic:
            semantic = ChromaIndex(config)
            semantic.ensure(index.file_manifest())
            seen = {item["path"] for item in lexical}
            lexical.extend(item for item in semantic.query(args.query, limit=args.limit) if item["path"] not in seen)
        _print(lexical[: args.limit])
    elif args.command == "todo":
        if args.todo_command == "add":
            destination = "today" if args.today else f"project:{args.project}" if args.project else "inbox"
            parsed = nltime.parse(args.text)
            parent_line = None
            if args.parent:
                if args.parent.isdigit():
                    parent_line = int(args.parent)
                else:
                    parent = next((t for t in parse_tasks(config) if t.id == args.parent), None)
                    if parent is None:
                        raise TaskNotFoundError(f"Parent task not found: {args.parent}")
                    expected = _destination_path(config, destination).relative_to(config.vault).as_posix()
                    if parent.path != expected:
                        raise DeepOrbitError(f"Parent task lives in {parent.path}, not {expected}; pass --today/--project to match")
                    parent_line = parent.line
            task = add_task(
                config,
                parsed["text"] or args.text,
                destination=destination,
                scheduled=args.scheduled,
                due=args.due or parsed["date"],
                time=args.time or parsed["time"],
                priority=args.priority or parsed["priority"],
                recurrence=args.recur or parsed["recurrence"],
                parent_line=parent_line,
            )
            payload = asdict(task)
            payload["parsed"] = parsed
            _print(payload)
        elif args.todo_command == "list":
            tasks = parse_tasks(config)
            if args.md:
                print(_render_tasks_md(tasks, args.view))
            else:
                _print(_view_payload(tasks, args.view))
        elif args.todo_command == "set":
            updates: dict = {}
            if args.status:
                updates["status"] = args.status
            if args.due:
                updates["due"] = args.due
            if args.time:
                updates["time"] = args.time
            if args.priority:
                updates["priority"] = args.priority
            if args.recur:
                updates["recurrence"] = args.recur
            if not updates:
                raise DeepOrbitError("todo set requires at least one of --status/--due/--time/--priority/--recur")
            _print(asdict(update_task(config, args.id, **updates)))
        elif args.todo_command == "attach":
            source = Path(args.file).expanduser()
            if not source.is_file():
                raise DeepOrbitError(f"Attachment not found: {source}")
            task = next((t for t in parse_tasks(config) if t.id == args.id), None)
            if task is None:
                raise TaskNotFoundError(f"Task not found: {args.id}")
            attachments_dir = config.vault / "90_Attachments"
            attachments_dir.mkdir(parents=True, exist_ok=True)
            target = attachments_dir / source.name
            if target.exists():
                stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
                target = attachments_dir / f"{source.stem}-{stamp}{source.suffix}"
            shutil.copy2(source, target)
            rel = f"90_Attachments/{target.name}"
            updated = update_task(config, args.id, text=f"{task.text} ![[{rel}]]")
            _print({"path": rel, "task": asdict(updated)})
        else:
            _print(asdict(complete_task(config, args.id)))
    elif args.command == "remind":
        from . import remind as reminders

        if args.remind_command == "install":
            _print(reminders.install(config))
        elif args.deliver:
            _print([
                {"task": asdict(task), "delivery": reminders.deliver(config, task)}
                for task in reminders.check(config)
            ])
        else:
            _print([asdict(task) for task in reminders.check(config)])
    elif args.command == "agenda":
        _print({key: [asdict(x) for x in value] for key, value in agenda(config).items()})
    elif args.command == "status":
        _print(work_overview(config))
    elif args.command == "suggest":
        _print([asdict(item) for item in build_suggestions(config)])
    elif args.command == "sweep":
        _print(work_sweep(config, days=args.days, dry_run=args.dry_run))
    elif args.command == "cron":
        if args.cron_command == "add":
            _print(asdict(add_job(args.name, config.vault, args.instruction, every=args.every or "daily", at=args.at)))
        elif args.cron_command == "remove":
            _print(asdict(remove_job(args.name)))
        elif args.cron_command == "run-due":
            due = [asdict(job) for job in run_due()]
            if args.agent:
                from .agents import AGENTS

                configured = config.agent or {}
                name, mode = configured.get("name", ""), configured.get("mode", "")
                spec = AGENTS.get(name)
                for job in due:
                    if spec and mode in spec.modes:
                        argv = spec.modes[mode]
                        if mode == "print":
                            job["handoff"] = argv + [f"In vault {job['vault']}: {job['instruction']}"]
                        else:
                            job["handoff"] = argv
                            job["handoff_note"] = (
                                f"Start {name} in {mode} mode, then send: "
                                f"In vault {job['vault']}: {job['instruction']}"
                            )
                    else:
                        job["handoff_note"] = (
                            "No agent configured — run: deeporbit --vault . agent detect "
                            "then: deeporbit --vault . agent configure <name>"
                        )
            _print(due)
        elif args.cron_command in ("enable", "disable"):
            _print(asdict(set_enabled(args.name, args.cron_command == "enable")))
        else:
            _print([asdict(job) for job in list_jobs()])
    elif args.command == "recipe":
        if args.recipe_command == "run":
            _print(run_plan(config, args.name))
        else:
            _print([asdict(recipe) for recipe in list_recipes(config)])
    elif args.command == "hygiene":
        _print([asdict(finding) for finding in scan_hygiene(config)])
    elif args.command == "sync":
        _print(
            asdict(
                sync_vault(
                    config.vault,
                    pull=not args.no_pull,
                    push=not args.no_push,
                    message=args.message or None,
                )
            )
        )
    elif args.command == "repo-link":
        _print(write_pointer(config, args.repo, args.at, args.title, github=args.github))
    elif args.command in ("pause", "resume", "done"):
        target = {"pause": "paused", "resume": "active", "done": "done"}[args.command]
        _print(asdict(work_set_status(config, args.path, target)))
    elif args.command == "archive":
        _print(work_archive(config, args.path))
    elif args.command == "trash":
        _print(work_trash(config, args.path))
    elif args.command == "profile":
        if args.profile_command == "set":
            _print(profile_set_field(config, args.key, args.value))
        elif args.profile_command == "observe":
            _print(profile_observe(config, args.text, source=args.source))
        elif args.profile_command == "focus":
            _print(profile_set_focus(config, args.text))
        elif args.profile_command == "compact":
            _print(profile_compact(config))
        else:
            _print(profile_show(config))
    elif args.command == "calendar":
        path, count = export_ics(config, args.output, privacy_mode=args.privacy_mode)
        _print({"path": str(path), "events": count})
    elif args.command == "privacy":
        if args.privacy_command == "scan":
            results = []
            tagged = 0
            min_index = LEVELS.index(args.min_level)
            privacy_scan = config.privacy.get("scan", {})
            exclude = list(privacy_scan.get("exclude", []))
            for score in scan_vault(
                config.vault,
                index_dirs=config.index_dirs,
                exclude_dirs=exclude,
            ):
                # Effective level: frontmatter tag (explicit decision) overrides heuristic
                effective = score.existing_level if score.existing_level in LEVELS else score.level
                if LEVELS.index(effective) < min_index:
                    continue
                rel = str(Path(score.path).relative_to(config.vault))
                entry: dict = {
                    "path": rel,
                    "level": effective,
                    "heuristic_level": score.level,
                    "score": score.score,
                    "categories": score.categories,
                    "patterns": score.patterns,
                    "tagged": score.existing_level is not None,
                }
                if args.explain:
                    entry["explain"] = {
                        "raw_score": score.raw_score,
                        "length_factor": score.length_factor,
                        "source_factor": score.source_factor,
                        "voice_factor": score.voice_factor,
                        "filename_signal": score.filename_signal,
                    }
                results.append(entry)
                if args.tag and not args.dry_run:
                    note = Path(score.path)
                    updated = write_fields(note.read_text(encoding="utf-8"), {"privacy_level": score.level})
                    note.write_text(updated, encoding="utf-8")
                    tagged += 1
            _print({"dry_run": args.dry_run, "tagged": tagged, "count": len(results), "results": results})
        elif args.privacy_command == "verify":
            from .content_signals import extract_sensitive_excerpt

            th = DEFAULT_THRESHOLDS
            gray_low = th["high"] - 2
            gray_high = th["critical"] + 2
            privacy_scan_cfg = config.privacy.get("scan", {})
            exclude = list(privacy_scan_cfg.get("exclude", []))
            # Collect all keywords for excerpt extraction
            all_keywords: list[str] = []
            for _kws in PRIVACY_CATEGORIES.values():
                all_keywords.extend(_kws[1])
            items = []
            for score in scan_vault(
                config.vault,
                index_dirs=config.index_dirs,
                exclude_dirs=exclude,
            ):
                if not (gray_low <= score.score <= gray_high):
                    continue
                rel = str(Path(score.path).relative_to(config.vault))
                text = Path(score.path).read_text(encoding="utf-8", errors="ignore")
                excerpt = extract_sensitive_excerpt(text, all_keywords, max_chars=args.max_chars)
                items.append({
                    "path": rel,
                    "score": score.score,
                    "heuristic_level": score.level,
                    "categories": score.categories,
                    "source_factor": score.source_factor,
                    "voice_factor": score.voice_factor,
                    "excerpt": excerpt,
                })
            _print({"gray_zone": [gray_low, gray_high], "count": len(items), "items": items})
        elif args.privacy_command == "apply":
            decisions_path = Path(args.decisions)
            decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
            applied = 0
            errors = []
            for item in decisions:
                rel = item["path"]
                level = item["level"]
                if level not in LEVELS:
                    errors.append({"path": rel, "error": f"invalid level: {level}"})
                    continue
                note = config.vault / rel
                if not note.exists():
                    errors.append({"path": rel, "error": "file not found"})
                    continue
                if not args.dry_run:
                    updated = write_fields(note.read_text(encoding="utf-8"), {"privacy_level": level})
                    note.write_text(updated, encoding="utf-8")
                applied += 1
            _print({"dry_run": args.dry_run, "applied": applied, "errors": errors})
    elif args.command == "serve":
        from .server import serve as serve_dashboard

        preference = args.agent
        if preference == "auto":
            configured = config.agent.get("name", "")
            if configured:
                preference = configured

        return serve_dashboard(
            config,
            host=args.host,
            port=args.port,
            open_browser=args.open,
            agent=preference,
            privacy_mode=args.privacy_mode,
        )

    elif args.command == "teach-me":
        from .teachme import export_to_teach_me

        result = export_to_teach_me(
            config,
            script=args.script,
            dirs=args.dirs,
            user=args.user,
            timeout=args.timeout,
        )
        _print(result)
        return 0

    elif args.command == "agent":
        from datetime import datetime, timezone

        from .agents import detect, resolve, status_payload
        from .config import save_agent

        if args.agent_command == "detect":
            _print([asdict(entry) for entry in detect(with_version=args.versions)])
        elif args.agent_command == "status":
            _print(status_payload(config.agent))
        elif args.agent_command == "configure":
            name, mode, argv = resolve(args.name, args.mode)
            entry = {
                "name": name,
                "mode": mode,
                "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            save_agent(config.vault, entry)
            _print({"saved": entry, "argv": argv})
        elif args.agent_command == "clear":
            save_agent(config.vault, None)
            _print({"saved": {}})
        return 0

    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv == ["__schema"]:
            _print(build_schema(parser()))
            return 0
        return run(parser().parse_args(argv))
    except (DeepOrbitError, RuntimeError, ValueError) as exc:
        print(json.dumps({"error": getattr(exc, "code", exc.__class__.__name__), "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
