#!/usr/bin/env python3
"""Fast, fail-open runtime hook adapter for DeepOrbit."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from deeporbit.config import load_config  # noqa: E402
from deeporbit.doctor import diagnose  # noqa: E402
from deeporbit.links import list_links  # noqa: E402
from deeporbit.git_sync import sync_vault  # noqa: E402

PROFILE_PATH = "99_System/Profile.md"
ANALYTICAL_MODE_PATH = "99_System/Prompts/Analytical_Truth_Mode.md"
STATE_FILE = "hook_state.json"
SYNC_STATE_FILE = "git_sync_state.json"
SYNC_DEBOUNCE_SECONDS = 120
TRACKED_SUFFIXES = {
    ".md",
    ".markdown",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".docx",
    ".xlsx",
    ".pptx",
    ".csv",
    ".tsv",
    ".txt",
}
IGNORED_DIRS = {
    ".git",
    ".obsidian",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "site",
}


def find_vault(payload: dict) -> Path | None:
    candidates = [
        payload.get("cwd"),
        payload.get("workspace"),
        payload.get("workspace_dir"),
        os.environ.get("DEEPORBIT_VAULT"),
        os.getcwd(),
    ]
    for raw in candidates:
        if not raw:
            continue
        path = Path(raw).expanduser().resolve()
        for candidate in [path, *path.parents]:
            if (candidate / "deeporbit.json").exists():
                return candidate

    try:
        links = list_links()
    except Exception:
        return None
    default = next((link for link in links if link.is_default), None)
    if default and (default.path / "deeporbit.json").exists():
        return default.path.resolve()
    for link in links:
        if (link.path / "deeporbit.json").exists():
            return link.path.resolve()
    return None


def _collect_profile_fields(profile_path: Path) -> list[str]:
    if not profile_path.exists():
        return []
    text = profile_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    fields: list[str] = []
    for line in text[3:end].splitlines():
        if not line.strip():
            continue
        if line.startswith(("-", " ", "\t")) or line.lstrip().startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            if value.strip():
                fields.append(f"{key.strip()}={value.strip()}")
    return fields


def _load_prompt(vault: Path) -> str:
    for candidate in (vault / "DeepOrbitPrompt.md", ROOT / "DeepOrbitPrompt.md"):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").strip()
    return ""


def _build_session_context(vault: Path, status: dict) -> str:
    cache = status.get("cache", {})
    parts: list[str] = []
    prompt = _load_prompt(vault)
    if prompt:
        parts.append(prompt)
        parts.append("--- DeepOrbit runtime status ---")
    parts.extend(
        [
            f"DeepOrbit vault: {status['vault']}",
            f"Indexed files: {cache.get('indexed_files', '?')}",
        ]
    )
    profile_fields = _collect_profile_fields(vault / PROFILE_PATH)
    if profile_fields:
        parts.append("Profile fields: " + ", ".join(profile_fields))
    else:
        parts.append("Profile fields not found yet; run `deeporbit --vault . init` to materialize profile defaults.")
    if (vault / ANALYTICAL_MODE_PATH).exists():
        parts.append(
            "Analytical truth mode protocol: `99_System/Prompts/Analytical_Truth_Mode.md` "
            "(objective, first-principles, long-chain analysis)."
        )
    return "\n".join(parts)


def _codex_hook_event(event: str) -> str:
    return {
        "session-start": "SessionStart",
        "file-change": "PostToolUse",
    }.get(event, event)


def _state_path(config) -> Path:
    return config.cache_dir / STATE_FILE


def _should_track(relpath: Path) -> bool:
    if relpath.suffix.lower() not in TRACKED_SUFFIXES:
        return False
    parts = relpath.parts
    if any(part.startswith(".") for part in parts[:-1]):
        return False
    if any(part in IGNORED_DIRS for part in parts[:-1]):
        return False
    if len(parts) >= 2 and parts[0] == "99_System" and parts[1] == "DeepOrbit":
        return False
    return True


def _scan_snapshot(vault: Path) -> dict[str, dict[str, int]]:
    snapshot: dict[str, dict[str, int]] = {}
    for path in vault.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relpath = path.relative_to(vault)
        if not _should_track(relpath):
            continue
        stat = path.stat()
        snapshot[str(relpath)] = {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
    return snapshot


def _load_snapshot(config) -> dict[str, dict[str, int]]:
    path = _state_path(config)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    files = raw.get("files", raw)
    return files if isinstance(files, dict) else {}


def _save_snapshot(config, files: dict[str, dict[str, int]]) -> None:
    path = _state_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"files": files}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sync_state_path(config) -> Path:
    return config.cache_dir / SYNC_STATE_FILE


def _load_sync_state(config) -> dict:
    path = _sync_state_path(config)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_sync_state(config, state: dict) -> None:
    path = _sync_state_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _maybe_sync_git(vault: Path, config) -> None:
    state = _load_sync_state(config)
    now = datetime.now(timezone.utc).timestamp()
    last_sync = float(state.get("last_sync_ts", 0.0) or 0.0)
    if last_sync and now - last_sync < SYNC_DEBOUNCE_SECONDS:
        return
    try:
        result = sync_vault(vault)
    except Exception as exc:  # Hooks must fail open.
        print(f"DeepOrbit hook warning: git sync skipped: {exc}", file=sys.stderr)
        return
    if result.git:
        state["last_sync_ts"] = now
        state["last_sync_reason"] = result.reason or ("committed" if result.committed else "clean")
        _save_sync_state(config, state)


def _format_change_summary(vault: Path, previous: dict[str, dict[str, int]], current: dict[str, dict[str, int]]) -> str:
    created = sorted(path for path in current if path not in previous)
    modified = sorted(path for path in current if path in previous and current[path] != previous[path])
    deleted = sorted(path for path in previous if path not in current)
    if not (created or modified or deleted):
        return ""
    label = vault.name or str(vault)
    parts = [f"[{label}]"]
    if created:
        parts.append("[created] " + ", ".join(created))
    if modified:
        parts.append("[modified] " + ", ".join(modified))
    if deleted:
        parts.append("[deleted] " + ", ".join(deleted))
    return " ".join(parts)


def emit(runtime: str, event: str, context: str = "") -> None:
    if runtime in {"gemini", "codex"}:
        hook_event = _codex_hook_event(event) if runtime == "codex" else event
        print(json.dumps({"hookSpecificOutput": {"hookEventName": hook_event, "additionalContext": context}}))
    elif runtime in {"kimi", "claude"}:
        print(context)
    else:
        print(json.dumps({"context": context}))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", choices=["kimi", "gemini", "openclaw", "codex", "claude", "omp"], required=True)
    parser.add_argument("--event", choices=["session-start", "file-change"], required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        vault = find_vault(payload)
        if not vault:
            emit(args.runtime, args.event)
            return 0
        config = load_config(vault)
        if args.event == "file-change":
            config.cache_dir.mkdir(parents=True, exist_ok=True)
            previous = _load_snapshot(config)
            current = _scan_snapshot(vault)
            summary = _format_change_summary(vault, previous, current)
            (config.cache_dir / "dirty").touch()
            emit(args.runtime, args.event, summary)
            _maybe_sync_git(vault, config)
            _save_snapshot(config, _scan_snapshot(vault))
        else:
            status = diagnose(config)
            context = _build_session_context(vault, status)
            emit(args.runtime, args.event, context)
            _save_snapshot(config, _scan_snapshot(vault))
    except Exception as exc:  # Hooks must fail open.
        print(f"DeepOrbit hook warning: {exc}", file=sys.stderr)
        emit(args.runtime, args.event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

