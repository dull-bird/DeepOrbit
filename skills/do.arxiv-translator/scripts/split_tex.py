#!/usr/bin/env python3
"""Split a monolithic LaTeX main file into per-section sub-files.

Usage:
    python3 split_tex.py MAIN.tex [--cjk-font "Noto Sans CJK SC"] [--dry-run]

- Writes each top-level `\\section{...}` block to `sections/NN_slug.tex`
  next to MAIN.tex and rewrites MAIN.tex to `\\input{sections/NN_slug}`.
- Optionally injects `xeCJK` + `\\setCJKmainfont{...}` into the preamble.
- Idempotent: a main file without top-level sections (already split) is a
  no-op. Existing section files are never overwritten.
- Prints a JSON report to stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SECTION_RE = re.compile(r"^\\section\{(.+?)\}\s*$", re.MULTILINE)


def slugify(title: str, index: int) -> str:
    words = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_").lower()
    return f"{index:02d}_{words or 'section'}"


def split_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (skeleton, [(slug, body)]) splitting at top-level \\section lines."""
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return text, []
    skeleton = text[: matches[0].start()]
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.start() : end].rstrip() + "\n"
        slug = slugify(match.group(1), index + 1)
        sections.append((slug, body))
        skeleton += f"\\input{{sections/{slug}}}\n\n"
    return skeleton, sections


def inject_cjk(text: str, font: str) -> tuple[str, bool]:
    if "xeCJK" in text:
        return text, False
    injection = f"\\usepackage{{xeCJK}}\n\\setCJKmainfont{{{font}}}\n"
    match = re.search(r"^\\documentclass.*$", text, re.MULTILINE)
    if match:
        return text[: match.end()] + "\n" + injection + text[match.end() :], True
    return injection + text, True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("main_tex", type=Path)
    parser.add_argument("--cjk-font", help="Inject xeCJK preamble with this CJK font")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    args = parser.parse_args(argv)

    main_tex: Path = args.main_tex
    text = main_tex.read_text(encoding="utf-8")
    skeleton, sections = split_sections(text)
    report: dict = {"main": str(main_tex), "sections": [], "cjk_injected": False, "changed": False}
    if not sections:
        report["note"] = "no top-level sections; already split or single-section document"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    sections_dir = main_tex.parent / "sections"
    written: list[str] = []
    skipped: list[str] = []
    for slug, body in sections:
        target = sections_dir / f"{slug}.tex"
        if target.exists():
            skipped.append(str(target))
            continue
        written.append(str(target))
        if not args.dry_run:
            sections_dir.mkdir(exist_ok=True)
            target.write_text(body, encoding="utf-8")

    cjk_injected = False
    if args.cjk_font:
        skeleton, cjk_injected = inject_cjk(skeleton, args.cjk_font)
    if not args.dry_run:
        main_tex.write_text(skeleton, encoding="utf-8")
    report.update(
        sections=written,
        skipped_existing=skipped,
        cjk_injected=cjk_injected,
        changed=not args.dry_run,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
