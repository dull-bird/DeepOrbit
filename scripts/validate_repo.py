#!/usr/bin/env python3
"""Validate DeepOrbit's cross-runtime repository contracts."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    skill_dirs = sorted((ROOT / "skills").glob("do.*"))
    skills: set[str] = set()
    for directory in skill_dirs:
        path = directory / "SKILL.md"
        if not path.exists():
            fail(f"Missing {path.relative_to(ROOT)}", errors)
            continue
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not match:
            fail(f"Missing frontmatter: {path.relative_to(ROOT)}", errors)
            continue
        try:
            frontmatter = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            fail(f"Invalid YAML frontmatter {path.relative_to(ROOT)}: {exc}", errors)
            continue
        name = frontmatter.get("name") if isinstance(frontmatter, dict) else None
        description = frontmatter.get("description") if isinstance(frontmatter, dict) else None
        if name != directory.name:
            fail(f"Skill name mismatch: {directory.name}", errors)
        else:
            skills.add(name.removeprefix("do."))
        if not isinstance(description, str) or not description.strip():
            fail(f"Missing description: {directory.name}", errors)
        if "[TODO" in text:
            fail(f"Placeholder remains: {directory.name}", errors)

    command_dir = ROOT / "commands" / "do"
    md = {path.stem for path in command_dir.glob("*.md")}
    toml = {path.stem for path in command_dir.glob("*.toml")}
    if md != toml:
        fail(f"Command format mismatch: md-only={sorted(md-toml)}, toml-only={sorted(toml-md)}", errors)
    if skills != md:
        fail(f"Skill/command mismatch: no-command={sorted(skills-md)}, no-skill={sorted(md-skills)}", errors)

    for path in [ROOT / "package.json", ROOT / "gemini-extension.json", ROOT / "kimi.plugin.json", ROOT / ".codex-plugin" / "plugin.json", ROOT / "integrations" / "runtime-profiles.json"]:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"Invalid JSON {path.relative_to(ROOT)}: {exc}", errors)

    searchable = [ROOT / "README.md", ROOT / "README_CN.md", ROOT / "DeepOrbitPrompt.md", *skill_dirs]
    for item in searchable:
        paths = [item / "SKILL.md"] if item.is_dir() else [item]
        for path in paths:
            if path.exists() and re.search(r"ralph", path.read_text(encoding="utf-8"), re.IGNORECASE):
                fail(f"Removed loop dependency still referenced: {path.relative_to(ROOT)}", errors)

    expected = len(skills)
    for readme in (ROOT / "README.md", ROOT / "README_CN.md"):
        text = readme.read_text(encoding="utf-8")
        if str(expected) not in text:
            fail(f"{readme.name} does not mention current skill count {expected}", errors)

    if errors:
        print("DeepOrbit contract validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"DeepOrbit contracts OK: {len(skills)} skills, {len(md)} paired commands, 4 runtime profiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
