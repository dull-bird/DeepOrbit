"""Minimal YAML-frontmatter field reader/writer with no runtime dependencies.

Only flat `key: value` fields are supported — that is all DeepOrbit workflows
use. Everything else in the file (nested YAML, body, comments) is preserved
byte-for-byte.
"""

from __future__ import annotations


def read_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    if not text.startswith("---"):
        return fields
    end = text.find("\n---", 3)
    if end == -1:
        return fields
    for line in text[3:end].splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-", "#")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def write_fields(text: str, updates: dict[str, str]) -> str:
    """Set flat frontmatter fields, preserving all other content and order."""
    lines = text.splitlines(keepends=True)
    end_idx: int | None = None
    if text.startswith("---"):
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
    if end_idx is None:
        header = ["---\n", *[f"{key}: {value}\n" for key, value in updates.items()], "---\n", "\n"]
        return "".join(header) + text
    remaining = dict(updates)
    for i in range(1, end_idx):
        line = lines[i]
        if ":" in line and not line.startswith((" ", "\t", "-", "#")):
            key = line.split(":", 1)[0].strip()
            if key in remaining:
                lines[i] = f"{key}: {remaining.pop(key)}\n"
    lines[end_idx:end_idx] = [f"{key}: {value}\n" for key, value in remaining.items()]
    return "".join(lines)
