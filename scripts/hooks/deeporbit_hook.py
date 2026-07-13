#!/usr/bin/env python3
"""Fast, fail-open runtime hook adapter for DeepOrbit."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from deeporbit.config import load_config  # noqa: E402
from deeporbit.doctor import diagnose  # noqa: E402


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
    return None


def emit(runtime: str, event: str, context: str = "") -> None:
    if runtime == "gemini":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}))
    elif runtime == "codex":
        print(json.dumps({"additional_context": context}))
    elif runtime == "kimi":
        print(context)
    else:
        print(json.dumps({"context": context}))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", choices=["kimi", "gemini", "openclaw", "codex"], required=True)
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
            (config.cache_dir / "dirty").touch()
            emit(args.runtime, args.event)
        else:
            status = diagnose(config)
            context = "DeepOrbit vault: {vault}; indexed files: {count}; pending local refresh is checked before retrieval.".format(
                vault=status["vault"], count=status["cache"]["indexed_files"]
            )
            emit(args.runtime, args.event, context)
    except Exception as exc:  # Hooks must fail open.
        print(f"DeepOrbit hook warning: {exc}", file=sys.stderr)
        emit(args.runtime, args.event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
