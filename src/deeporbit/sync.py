"""Managed-file synchronization: version tags and conflict-safe prompt updates.

Users edit their prompt files; upstream evolves. The conflict protocol:

- System-owned content lives only inside named blocks:
      <!-- deeporbit-managed:NAME -->
      *(managed by DeepOrbit <version> — edit outside these markers)*
      ...content...
      <!-- /deeporbit-managed:NAME -->
  Refresh replaces block contents wholesale. Text outside markers is
  user-owned and is never touched.
- A file authored by DeepOrbit (vanilla or an older managed generation) MAY be
  replaced fully. Detecting "authored by us": a managed block exists, or the
  first heading mentions DeepOrbit and no user marker is present.
- Anything else merges block-wise and reports exactly what changed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import __version__

BLOCK_RE = "<!-- deeporbit-managed:{name} -->"


@dataclass(slots=True)
class SyncResult:
    path: str
    action: str  # replaced | updated-block | appended-block | unchanged | user-file-skipped
    detail: str = ""


def _markers(name: str) -> tuple[str, str]:
    return f"<!-- deeporbit-managed:{name} -->", f"<!-- /deeporbit-managed:{name} -->"


def render_block(name: str, content: str) -> str:
    start, end = _markers(name)
    return f"{start}\n*(managed by DeepOrbit {__version__} — edit outside these markers)*\n{content.rstrip()}\n{end}"


def sync_block(text: str, name: str, content: str) -> tuple[str, str]:
    """Insert or replace a managed block. Returns (new_text, action).

    Start markers tolerate a legacy suffix (`:2026-07-25`) so blocks written
    before the protocol stabilized are still found and replaced.
    """
    start, end = _markers(name)
    block = render_block(name, content)
    start_prefix = start[: -len(" -->")]
    pattern = re.compile(re.escape(start_prefix) + r"[^\n]*-->.*?" + re.escape(end), re.S)
    if pattern.search(text):
        replaced = pattern.sub(lambda _: block, text, count=1)
        return (replaced, "updated-block") if replaced != text else (text, "unchanged")
    sep = "" if text.endswith("\n\n") else "\n" if text.endswith("\n") else "\n\n"
    return text + sep + block + "\n", "appended-block"


def authored_by_deeporbit(text: str) -> bool:
    """A file counts as DeepOrbit-authored only when its first heading names
    DeepOrbit. The presence of a managed block is NOT authorship — managed
    blocks coexist with user content by design, and mistaking them for
    authorship makes the next sync wipe the user's text (2026-07 incident)."""
    first_heading = next((line for line in text.splitlines() if line.startswith("#")), "")
    return "deeporbit" in first_heading.lower()


def extract_section(prompt_text: str, heading: str) -> str:
    """Pull one ## section out of the canonical prompt, without the heading."""
    match = re.search(re.escape(heading) + r"\n(.*?)(?=\n## |\Z)", prompt_text, re.S)
    return match.group(1).strip() if match else ""


def agents_stub(vault_path: str) -> str:
    return f"""# DeepOrbit on this vault

<!-- deeporbit-version: {__version__} -->
Canonical runtime context: `99_System/DeepOrbit/repo/DeepOrbitPrompt.md`
(user rules live in root `DeepOrbitPrompt.md` — read both).

1. Read `deeporbit.json` for language, configured directories, and schema.
2. Use the matching `do.*` skill when available; skills are the source of truth.
3. CLI: `deeporbit --vault \"{vault_path}\" <command>` (JSON in/out — no API keys
   inside DeepOrbit; the agent is the model).
4. Full machine-readable surface: `deeporbit --vault \"{vault_path}\" __schema`.
5. Skill relationship graph: `99_System/DeepOrbit/skills_graph.yaml`; WHEN rules:
   `99_System/Rules/`.
"""


def claude_stub() -> str:
    return f"""# CLAUDE.md

<!-- deeporbit-version: {__version__} -->
@DeepOrbitPrompt.md

Canonical DeepOrbit runtime context: `99_System/DeepOrbit/repo/DeepOrbitPrompt.md`.
"""


def prompt_pointer_block(vault_path: str) -> str:
    return (
        "Canonical DeepOrbit context: `99_System/DeepOrbit/repo/DeepOrbitPrompt.md` "
        "(refreshed by `deeporbit init`). Skill graph: `99_System/DeepOrbit/skills_graph.yaml`. "
        f"CLI: `deeporbit --vault '{vault_path}' <command>` — JSON in/out, no API keys inside DeepOrbit."
    )


def sync_file(path, *, name: str, block_content: str, full_content: str | None = None, dry_run: bool = False) -> SyncResult:
    """Sync one prompt file per the conflict protocol.

    full_content given and file is DeepOrbit-authored → full replace.
    Otherwise block-merge. Never touches user text outside markers.
    """
    from pathlib import Path

    path = Path(path)
    rel = path.name
    if not path.exists():
        if full_content is None:
            return SyncResult(rel, "user-file-skipped", "file missing and no full content provided")
        if not dry_run:
            path.write_text(full_content, encoding="utf-8")
        return SyncResult(rel, "replaced", "created")
    text = path.read_text(encoding="utf-8")
    if full_content is not None and authored_by_deeporbit(text):
        if text == full_content:
            return SyncResult(rel, "unchanged")
        if not dry_run:
            path.write_text(full_content, encoding="utf-8")
        return SyncResult(rel, "replaced", "DeepOrbit-authored file refreshed")
    new_text, action = sync_block(text, name, block_content)
    if action != "unchanged" and not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return SyncResult(rel, action)
