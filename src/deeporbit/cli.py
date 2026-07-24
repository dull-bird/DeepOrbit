from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .config import load_config
from .doctor import diagnose
from .errors import DeepOrbitError
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
from .tasks import add_task, agenda, complete_task, parse_tasks
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
    todo_sub.add_parser("list")
    done = todo_sub.add_parser("done")
    done.add_argument("id")
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
    cron_add.add_argument("--every", default="daily", help="hourly | daily | weekly | <N>h | <N>d")
    cron_sub.add_parser("list")
    cron_remove = cron_sub.add_parser("remove")
    cron_remove.add_argument("name")
    cron_sub.add_parser("run-due", help="Report jobs whose interval elapsed and stamp their last run")
    for toggle in ("enable", "disable"):
        toggle_cmd = cron_sub.add_parser(toggle)
        toggle_cmd.add_argument("name")
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
    return root



def _link_dict(link) -> dict:
    payload = asdict(link)
    payload["path"] = str(link.path)
    return payload


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
            _print(asdict(add_task(config, args.text, destination=destination, scheduled=args.scheduled, due=args.due)))
        elif args.todo_command == "list":
            _print([asdict(x) for x in parse_tasks(config)])
        else:
            _print(asdict(complete_task(config, args.id)))
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
            _print(asdict(add_job(args.name, config.vault, args.instruction, args.every)))
        elif args.cron_command == "remove":
            _print(asdict(remove_job(args.name)))
        elif args.cron_command == "run-due":
            _print([asdict(job) for job in run_due()])
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

        return serve_dashboard(
            config,
            host=args.host,
            port=args.port,
            open_browser=args.open,
            agent=args.agent,
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
