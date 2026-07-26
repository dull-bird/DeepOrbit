"""Experimental CLI Schema v1 exporter (https://github.com/cli-schema/cli-schema).

Walks the argparse command tree so the emitted document never drifts from the
real parser. Operational semantics (intent, output formats, examples) are
declared explicitly in `_METADATA` — never guessed from the parser shape.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__

_JSON_OUTPUT = {"formats": ["json"]}

# Explicit operational metadata keyed by command path. Paths ending at a
# namespace (e.g. ("todo",)) describe the namespace itself.
_METADATA: dict[tuple[str, ...], dict] = {
    ("init",): {
        "summary": "Initialize or upgrade a DeepOrbit vault (folders, config, materialized workflows, portable runtime bundle)",
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
        "examples": ["deeporbit --vault ~/Documents/MyVault init --source /path/to/DeepOrbit"],
    },
    ("doctor",): {
        "summary": "Diagnose optional capabilities (Obsidian CLI, ChromaDB, plugins) and vault skeleton integrity; --strict exits 1 on skeleton gaps or root violations (zero-token cron check)",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
        "examples": ["deeporbit --vault @main doctor --strict"],
    },
    ("triage",): {
        "summary": "Classify stray files deterministically: valuable → inbox/research/notes/resources, code/secrets → out-of-vault, junk → trash. Read-only; execution is agent + user approval",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
        "examples": ["deeporbit --vault @main triage", "deeporbit --vault @main triage stray.md olddir/"],
    },
    ("sync-prompts",): {
        "summary": "Sync DeepOrbit-managed prompt content (DeepOrbitPrompt.md/AGENTS.md/CLAUDE.md) via conflict-safe managed blocks; user text outside markers is never touched",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
        "examples": ["deeporbit --vault @main sync-prompts --dry-run", "deeporbit --vault @main sync-prompts"],
    },
    ("organize",): {
        "summary": "Re-file projects/research items by frontmatter status (active at section root, paused in Paused/, archived in Archived/); dry-run unless --apply",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
        "examples": ["deeporbit --vault @main organize", "deeporbit --vault @main organize --apply"],
    },
    ("open",): {
        "summary": "Open a note through Obsidian CLI, obsidian:// URI, or path fallback",
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("index",): {
        "summary": "Build or inspect the device-local lexical (and optional semantic) index",
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("rag",): {
        "summary": "Query the local vault index",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
        "examples": ["deeporbit --vault @main rag \"index tracking\" --limit 5"],
    },
    ("todo",): {"summary": "Capture, list, and complete Markdown tasks"},
    ("todo", "add"): {
        "summary": "Add a task to the inbox, today, or a project; natural-language time is parsed from the text and explicit flags override it",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": False, "scope": "directory"},
        "output": _JSON_OUTPUT,
        "examples": ["deeporbit --vault @main todo add \"今晚七点跟丽丽吃饭\""],
    },
    ("todo", "list"): {
        "summary": "List all parsed tasks (flat/board/timeline/progress views; --md renders Markdown tables)",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("todo", "done"): {
        "summary": "Complete a task by its stable ^do-* block ID",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("todo", "set"): {
        "summary": "Update status/due/time/priority/recurrence of an existing task",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("todo", "attach"): {
        "summary": "Copy a file into 90_Attachments and append a ![[...]] embed to the task",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": False, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("remind",): {"summary": "Due-task reminders: launchd polling plus alerter/osascript delivery"},
    ("remind", "check"): {
        "summary": "List due reminders as JSON; --deliver sends notifications and records state",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("remind", "install"): {
        "summary": "Install the launchd agent (StartInterval 60) that runs remind check --deliver",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("agenda",): {
        "summary": "Group overdue, today, upcoming, and unscheduled tasks",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("calendar",): {
        "summary": "Export dated tasks to a portable ICS snapshot",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("status",): {
        "summary": "Overview of every work item (any note with a status field) by lifecycle status",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("serve",): {
        "summary": "Serve the local web dashboard with an ACP agent bridge (127.0.0.1 only)",
        "longRunning": True,
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("hygiene",): {
        "summary": "Detect attachment misplacements and code files inside the vault",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("sync",): {
        "summary": "Synchronize the vault with Git (pull, commit, push when needed)",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("sweep",): {
        "summary": "Auto-pause active items idle for more than N days (excludes read-only zones and Wiki)",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("repo-link",): {
        "summary": "Write a canonical external-repo pointer note (repo + host + user + os)",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("pause",): {
        "summary": "Mark a note as paused (projects/research items move into the section's Paused/ folder)",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("resume",): {
        "summary": "Return a paused note to active (moves it back to the section root)",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("done",): {
        "summary": "Mark a note as done (ready for archiving)",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("archive",): {
        "summary": "Archive a note or project folder with archived metadata (projects/research items move into the section's Archived/ folder, everything else into the system Archive)",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": False, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("trash",): {
        "summary": "Move a path into .trash (reversible deletion; protected paths refused)",
        "tags": ["write", "dangerous"],
        "intent": {"destructive": True, "idempotent": False, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("profile",): {"summary": "Show and maintain the vault's user profile"},
    ("suggest",): {
        "summary": "Prioritized suggestions derived from vault state (seed for mentor and dreaming)",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("suggest", "feedback"): {
        "summary": "Record accepted/dismissed feedback for a suggestion rule (device-local counters; heartbeat reports acceptance rates)",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": False, "scope": "global"},
        "output": _JSON_OUTPUT,
        "examples": ["deeporbit --vault @main suggest feedback stalled-project accepted"],
    },
    ("heartbeat",): {
        "summary": "Deterministic context pack for the do.heartbeat patrol: suggestions, counts, due reminders, snapshot delta, facts, WHEN rules, feedback rates",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "directory"},
        "output": _JSON_OUTPUT,
    },
    ("recipe",): {"summary": "List, resolve, and schedule composable workflow recipes"},
    ("recipe", "schedule"): {
        "summary": "Idempotently register a cron job (recipe-<name>) from the recipe's schedule: frontmatter",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
        "examples": ["deeporbit --vault @main recipe schedule weekly-review"],
    },
    ("cron",): {"summary": "Schedule recurring DeepOrbit workflows (device-local registry)"},
    ("cron", "add"): {
        "summary": "Register a recurring (--every) or one-shot (--at) natural-language workflow for a vault",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
        "examples": ["deeporbit --vault @main cron add weekly-report \"提醒我写周报并先给我草稿\" --at 2026-07-25T19:00"],
    },
    ("cron", "list"): {
        "summary": "List scheduled jobs",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("cron", "remove"): {
        "summary": "Remove a scheduled job",
        "tags": ["write", "dangerous"],
        "intent": {"destructive": True, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("cron", "run-due"): {
        "summary": "Report jobs whose interval elapsed and stamp their last run",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": False, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("cron", "enable"): {
        "summary": "Enable a scheduled job",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("cron", "disable"): {
        "summary": "Disable a scheduled job without removing it",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("profile", "show"): {
        "summary": "Show profile fields and observations",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("profile", "set"): {
        "summary": "Set a stable profile frontmatter field (role, domains, preferences…)",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("profile", "observe"): {
        "summary": "Append a timestamped, source-tagged observation to the profile",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": False, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("profile", "focus"): {
        "summary": "Replace the Focus section with a distilled identity summary",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": False, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("profile", "compact"): {
        "summary": "Archive raw profile observations after distillation",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "file"},
        "output": _JSON_OUTPUT,
    },
    ("link",): {"summary": "Register and resolve external DeepOrbit vaults (device-local registry)"},
    ("link", "add"): {
        "summary": "Register a vault path under a name, with an optional purpose description",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("link", "list"): {
        "summary": "Show registered vaults, markers, descriptions, and the default",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("link", "route"): {
        "summary": "Pick the best vault for a natural-language request",
        "tags": ["read"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("link", "remove"): {
        "summary": "Unregister a vault",
        "tags": ["write", "dangerous"],
        "intent": {"destructive": True, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("link", "default"): {
        "summary": "Set or show the default link used for `@` resolution",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
    ("link", "describe"): {
        "summary": "Set or refine a vault's purpose description (drives request routing)",
        "tags": ["write"],
        "intent": {"destructive": False, "idempotent": True, "scope": "global"},
        "output": _JSON_OUTPUT,
    },
}

_TYPE_MAP = {int: "integer", float: "number", str: "string", Path: "string"}


def _subparsers_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _param_type(action: argparse.Action) -> str:
    if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
        return "boolean"
    if action.choices:
        return "enum"
    return _TYPE_MAP.get(action.type, "string") if action.type else "string"


def _parameter(action: argparse.Action) -> dict:
    param: dict = {"role": "flag", "name": "", "type": _param_type(action), "required": False}
    if action.option_strings:
        long_names = [opt for opt in action.option_strings if opt.startswith("--")]
        short_names = [opt for opt in action.option_strings if not opt.startswith("--")]
        param["name"] = (long_names[0] if long_names else action.option_strings[0]).lstrip("-")
        if short_names:
            param["shortName"] = short_names[0].lstrip("-")
        param["required"] = bool(action.required)
        if action.option_strings == ["--dry-run"]:
            param["role"] = "dryRun"
    else:
        param["role"] = "positional"
        param["name"] = action.metavar or action.dest
        param["required"] = action.nargs not in ("?", "*")
        if action.nargs in ("*", "+"):
            param["variadic"] = True
    if action.help:
        param["summary"] = action.help
    if action.choices:
        param["enumValues"] = [str(choice) for choice in action.choices]
    if isinstance(action, argparse._StoreTrueAction):
        param["defaultValue"] = "false"
    elif action.default not in (None, False) and not callable(action.default):
        param["defaultValue"] = str(action.default)
    return param


def _parameters(parser: argparse.ArgumentParser) -> list[dict]:
    return [
        _parameter(action)
        for action in parser._actions
        if not isinstance(action, (argparse._HelpAction, argparse._SubParsersAction))
    ]


def _command(name: str, path: tuple[str, ...], parser: argparse.ArgumentParser, help_map: dict[str, str]) -> dict:
    full_path = (*path, name)
    command: dict = {"name": name}
    if path:
        command["path"] = list(path)
    metadata = _METADATA.get(full_path, {})
    summary = metadata.get("summary") or help_map.get(name)
    if summary:
        command["summary"] = summary
    parameters = _parameters(parser)
    if parameters:
        command["parameters"] = parameters
    for key in ("tags", "intent", "output", "examples", "notes", "usage"):
        if key in metadata:
            command[key] = metadata[key]
    return command


def _namespace(name: str, path: tuple[str, ...], parser: argparse.ArgumentParser, help_map: dict[str, str]) -> dict:
    full_path = (*path, name)
    namespace: dict = {"segment": name}
    metadata = _METADATA.get(full_path, {})
    summary = metadata.get("summary") or help_map.get(name)
    if summary:
        namespace["summary"] = summary
    options = _parameters(parser)
    if options:
        namespace["options"] = options
    commands, namespaces = _children(full_path, parser)
    if commands:
        namespace["commands"] = commands
    if namespaces:
        namespace["namespaces"] = namespaces
    return namespace


def _children(path: tuple[str, ...], parser: argparse.ArgumentParser) -> tuple[list[dict], list[dict]]:
    action = _subparsers_action(parser)
    if action is None:
        return [], []
    help_map = {pseudo.dest: pseudo.help for pseudo in action._choices_actions}
    commands: list[dict] = []
    namespaces: list[dict] = []
    for name, subparser in action.choices.items():
        if _subparsers_action(subparser) is not None:
            namespaces.append(_namespace(name, path, subparser, help_map))
        else:
            commands.append(_command(name, path, subparser, help_map))
    return commands, namespaces


def build_schema(parser: argparse.ArgumentParser, *, version: str = __version__) -> dict:
    """Build a CLI Schema v1 document from the argparse command tree."""
    commands, namespaces = _children((), parser)
    return {
        "schemaVersion": 1,
        "name": "deeporbit",
        "version": version,
        "description": "Portable Agent Skills and local-first tooling for Obsidian knowledge systems",
        "tags": ["knowledge-management", "obsidian", "agents", "experimental"],
        "requiresAuth": False,
        "reservedMetaCommands": ["__schema"],
        "environment": {
            "variables": [
                {
                    "name": "XDG_CONFIG_HOME",
                    "required": False,
                    "description": "Base directory holding the device-local link registry",
                    "defaultValue": "~/.config",
                },
                {
                    "name": "XDG_CACHE_HOME",
                    "required": False,
                    "description": "Base directory holding per-vault search indexes",
                    "defaultValue": "~/.cache",
                },
            ],
            "configFiles": [
                {
                    "path": "deeporbit.json",
                    "description": "Vault-root config: vault ID, language, indexed directories",
                    "required": True,
                },
                {
                    "path": "~/.config/deeporbit/links.json",
                    "description": "Device-local registry of linked vaults used by `@name` resolution",
                    "required": False,
                },
                {
                    "path": "~/.config/deeporbit/reminders.json",
                    "description": "Device-local reminder delivery state (reminded/snooze records)",
                    "required": False,
                },
            ],
        },
        "globalOptions": [
            {
                "role": "flag",
                "name": "vault",
                "type": "string",
                "required": False,
                "summary": "Obsidian vault path, or `@name` / `@` to resolve the link registry",
                "defaultValue": ".",
            }
        ],
        "commands": commands,
        "namespaces": namespaces,
        "x-experimental": True,
    }
