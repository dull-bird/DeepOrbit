from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .calendar import export_ics
from .config import load_config
from .doctor import diagnose
from .errors import DeepOrbitError
from .openers import open_note
from .search import SearchIndex
from .semantic import ChromaIndex
from .tasks import add_task, agenda, complete_task, parse_tasks
from .vault import initialize


def _print(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="deeporbit")
    root.add_argument("--vault", default=".", help="Obsidian vault path")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("doctor")
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
    calendar = commands.add_parser("calendar")
    calendar.add_argument("action", choices=["export"])
    calendar.add_argument("--output", type=Path)
    return root


def run(args: argparse.Namespace) -> int:
    vault = Path(args.vault)
    if args.command == "init":
        result = initialize(vault)
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
    elif args.command == "calendar":
        path, count = export_ics(config, args.output)
        _print({"path": str(path), "events": count})
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parser().parse_args(argv))
    except (DeepOrbitError, RuntimeError, ValueError) as exc:
        print(json.dumps({"error": getattr(exc, "code", exc.__class__.__name__), "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
