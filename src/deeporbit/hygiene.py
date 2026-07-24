"""Vault hygiene: deterministic detection of attachment and code-file problems.

Two rules, enforced by detection (not trust):

1. **Attachments** — images/binaries belong next to their owning note
   (`<note-dir>/assets/`) or in `99_System/Attachments/`; the vault root must
   stay clean, and orphans (no referencing note) get flagged.
2. **No code in the vault** — code lives in Git/local repos; notes point at
   them. `node_modules`, `dist`, and source files outside whitelisted system
   zones are findings, never "someone's choice".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".heic", ".tif", ".tiff"}
CODE_EXTS = {".js", ".ts", ".jsx", ".tsx", ".py", ".java", ".go", ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".sh"}
CODE_DIRS = {"node_modules", "dist", "build", "out", "target", "__pycache__", ".venv", "venv"}
WHITELIST_PREFIXES = (".obsidian", ".trash", ".git", "99_System/DeepOrbit", "99_System/Archive")
ATTACHMENT_OK_PARTS = ("assets", "99_System/Attachments", "99_System/Templates")


@dataclass(slots=True)
class Finding:
    kind: str  # root-attachment | stray-attachment | orphan-attachment | code-dir | code-file
    path: str
    detail: str
    action: str


def _whitelisted(config: Config, rel: str) -> bool:
    if rel.startswith(WHITELIST_PREFIXES):
        return True
    return any(rel == zone or rel.startswith(zone.rstrip("/") + "/") for zone in config.readonly_dirs)


def scan_hygiene(config: Config) -> list[Finding]:
    vault = config.vault
    findings: list[Finding] = []

    all_files = [p for p in vault.rglob("*") if p.is_file() and ".obsidian" not in p.parts and ".git" not in p.parts]
    md_texts: list[str] = [p.read_text(encoding="utf-8", errors="replace") for p in all_files if p.suffix == ".md"]

    for path in all_files:
        rel = path.relative_to(vault).as_posix()
        if _whitelisted(config, rel):
            continue
        suffix = path.suffix.lower()
        if any(part in CODE_DIRS for part in path.parts):
            findings.append(Finding("code-dir", rel, "build/dependency directory does not belong in a vault", "Move the project to a code repo; keep a pointer note here"))
            continue
        if suffix in CODE_EXTS:
            findings.append(Finding("code-file", rel, "source file in vault", "Move to a code repo (GitHub/local) and leave a `[[repo]]` pointer note"))
        if suffix in IMAGE_EXTS:
            if len(path.relative_to(vault).parts) == 1:
                findings.append(Finding("root-attachment", rel, "attachment at vault root", "Move to the owning note's assets/ or 99_System/Attachments/"))
            elif not any(part in ATTACHMENT_OK_PARTS for part in path.relative_to(vault).parts):
                findings.append(Finding("stray-attachment", rel, "image outside an assets/ folder", "Move beside the note that embeds it"))

    # orphan detection: exact filename or an explicit wikilink, never substrings
    body = "\n".join(md_texts)
    for finding in findings:
        if finding.kind in ("root-attachment", "stray-attachment"):
            name = Path(finding.path).name
            stem = Path(finding.path).stem
            if name not in body and f"[[{stem}" not in body:
                finding.kind = "orphan-attachment"
                finding.detail = "no note references this image"
                finding.action = "Archive or trash after confirming it is unused"

    # de-duplicate code-dir noise: report a code-dir once per top occurrence
    seen_dirs: set[str] = set()
    deduped: list[Finding] = []
    for finding in findings:
        if finding.kind == "code-dir":
            parts = finding.path.split("/")
            idx = next(i for i, part in enumerate(parts) if part in CODE_DIRS)
            top = "/".join(parts[: idx + 1])
            if top in seen_dirs:
                continue
            seen_dirs.add(top)
            finding.path = top
        deduped.append(finding)
    return deduped
