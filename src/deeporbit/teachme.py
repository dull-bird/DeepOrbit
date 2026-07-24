"""Export DeepOrbit vault knowledge into a Teach Me vault with provenance.

The export stages the vault's knowledge notes (default: 40_Wiki, 60_Notes,
30_Research) into a temporary directory and calls Teach Me's
`teach_me.py import --source obsidian` on it. Teach Me records the vault in
its `linked_vaults`, returns an `origin` provenance block, and produces a
`prompt_for_ai` that instructs the agent to distill knowledge points while
passing `origin` through to every `capture`/`assess` call — so imported
knowledge never mixes with knowledge Teach Me accumulates natively.

70_Family is never exported by default; read-only zones are always skipped.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import Config
from .errors import DeepOrbitError

DEFAULT_EXPORT_DIRS = ("40_Wiki", "60_Notes", "30_Research")
OPTIONAL_EXPORT_DIRS = ("15_Writings", "20_Projects", "70_Family")

SCRIPT_ENV = "TEACH_ME_SCRIPT"


class TeachMeError(DeepOrbitError):
    code = "TEACH_ME_ERROR"


def teach_me_candidates() -> list[Path]:
    """Common locations of teach_me.py, most specific first."""
    home = Path.home()
    return [
        home / ".claude" / "skills" / "teach-me" / "scripts" / "teach_me.py",
        home / ".agents" / "skills" / "teach-me" / "scripts" / "teach_me.py",
        home / ".codex" / "skills" / "teach-me" / "scripts" / "teach_me.py",
        home / ".omp" / "skills" / "teach-me" / "scripts" / "teach_me.py",
        home / "projects" / "teach-me-skill" / "skills" / "teach-me" / "scripts" / "teach_me.py",
    ]


def find_teach_me_script(explicit: str | None = None) -> Path:
    """Resolve the Teach Me runtime script.

    Order: explicit --script > $TEACH_ME_SCRIPT > known install locations.
    """
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return path
        raise TeachMeError(f"Teach Me script not found: {path}")
    env_path = os.environ.get(SCRIPT_ENV, "").strip()
    if env_path:
        path = Path(env_path).expanduser()
        if path.is_file():
            return path
        raise TeachMeError(f"{SCRIPT_ENV} points to a missing file: {path}")
    for candidate in teach_me_candidates():
        if candidate.is_file():
            return candidate
    raise TeachMeError(
        "Teach Me runtime not found. Install teach-me-skill or pass --script "
        f"/ set {SCRIPT_ENV}. See https://github.com/dull-bird/teach-me-skill"
    )


def select_export_notes(config: Config, dirs: list[str] | None = None) -> list[Path]:
    """Pick the vault notes eligible for Teach Me export.

    Defaults to knowledge dirs only. Read-only zones (external sync targets)
    and 70_Family are skipped unless their dir is passed explicitly.
    """
    vault = config.vault
    selected_dirs = list(dirs) if dirs else list(DEFAULT_EXPORT_DIRS)
    readonly = {entry.strip("/") for entry in config.readonly_dirs}
    notes: list[Path] = []
    for rel_dir in selected_dirs:
        root = vault / rel_dir
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            rel = path.relative_to(vault).as_posix()
            if any(rel == zone or rel.startswith(zone + "/") for zone in readonly):
                continue
            notes.append(path)
    return notes


def stage_notes(config: Config, notes: list[Path], staging: Path) -> list[str]:
    """Copy notes into a staging dir, preserving vault-relative paths."""
    staged: list[str] = []
    for note in notes:
        rel = note.relative_to(config.vault)
        target = staging / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(note, target)
        staged.append(rel.as_posix())
    return staged


def export_to_teach_me(
    config: Config,
    *,
    script: str | None = None,
    dirs: list[str] | None = None,
    user: str | None = None,
    timeout: float = 120.0,
) -> dict:
    """Stage vault knowledge and invoke `teach_me.py import` on it.

    Returns Teach Me's JSON output (import_id, origin, prompt_for_ai, …)
    plus DeepOrbit-side staging details.
    """
    teach_me = find_teach_me_script(script)
    notes = select_export_notes(config, dirs)
    if not notes:
        raise TeachMeError(
            "No exportable notes found. Default dirs: " + ", ".join(DEFAULT_EXPORT_DIRS)
        )

    vault_name = config.vault.name
    with tempfile.TemporaryDirectory(prefix="deeporbit-teachme-") as tmp:
        staging = Path(tmp) / vault_name
        staging.mkdir()
        staged = stage_notes(config, notes, staging)
        cmd = [
            sys.executable,
            str(teach_me),
            "import",
            "--source",
            "obsidian",
            "--path",
            str(staging),
            "--project",
            vault_name,
            "--phase",
            "deeporbit vault export",
            "--json",
        ]
        if user:
            cmd.extend(["--user", user])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            raise TeachMeError(f"teach_me.py import failed ({proc.returncode}): {proc.stderr.strip()}")
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise TeachMeError(f"teach_me.py returned non-JSON output: {proc.stdout[:200]}") from exc

    # The origin block must name the real vault, not the staging copy.
    origin = result.get("origin") or {}
    origin["source_path"] = str(config.vault)
    origin["vault_name"] = vault_name
    result["origin"] = origin
    result["path"] = str(config.vault)
    prompt = result.get("prompt_for_ai", "")
    if prompt:
        result["prompt_for_ai"] = prompt.replace(str(staging), str(config.vault))
    result["deeporbit"] = {
        "vault": str(config.vault),
        "vault_id": config.vault_id,
        "exported_notes": len(staged),
        "dirs": sorted({Path(rel).parts[0] for rel in staged}),
        "teach_me_script": str(teach_me),
    }
    return result
