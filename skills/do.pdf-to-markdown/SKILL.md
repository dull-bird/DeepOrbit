---
name: do.pdf-to-markdown
description: Convert PDF documents to high-fidelity Markdown with checkpointed page and section coverage verification. Use when the user asks to convert, transcribe, extract, or preserve a PDF as Markdown, especially for papers containing formulas, tables, figures, or multi-column layouts.
---

# PDF to Markdown

Preserve the source language and document structure. Use visual PDF reading for formulas, tables, and reading order; do not trust blind text extraction for complex layouts.

## 1. Build the manifest

Inspect the full PDF and write `<name>_manifest.md` beside it:

```markdown
---
deeporbit_workflow: 1
workflow_id: pdf-<date>-<slug>
status: active
source: <name>.pdf
output: <name>.md
---

# Conversion Manifest
- Total pages: N
- [ ] Cover and metadata (p.1)
- [ ] Abstract (p.1-2)
- [ ] Section 1 (p.2-5)
- [ ] References (p.N-2-N)
- Tables: T
- Figures: F
```

Every page must belong to a checklist item. If bundled image extraction is available, run:

```bash
python <skill-dir>/scripts/extract_images.py <input.pdf>
```

PyMuPDF is optional and is used only for embedded images, never as the sole text source.

## 2. Convert with checkpoints

For each unchecked section:

1. Visually read its page range.
2. Append it to `<name>.md` in reading order.
3. Preserve headings, paragraph breaks, lists, fenced code, footnotes, tables, and emphasis.
4. Transcribe math as `$...$` or `$$...$$`.
5. Reference extracted images with relative paths and source captions.
6. Compare paragraph, table, figure, and page coverage.
7. Mark that section checked only after its verification succeeds.

Continue in the same turn when feasible. If interrupted or context-limited, reread the manifest and resume at the first unchecked item. A runtime Goal or Tracker may mirror the overall objective, but the manifest remains authoritative. Do not use an external self-invoking loop.

## 3. Verify the whole document

- All manifest entries are checked.
- Every page is covered exactly once or its overlap is explained.
- Output headings match the source section list.
- Table and figure counts match.
- Code, math, links, and footnotes are intact.
- No source paragraphs were silently omitted.

Add a final conversion report with page, section, table, figure, image, and word counts. Keep the manifest when an audit trail is useful; otherwise ask before deleting it.

## 4. Final output

Write frontmatter at line 1:

```yaml
---
type: note
title: "<Document Title>"
source: "[[<name>.pdf]]"
created: YYYY-MM-DD
tags: [pdf-conversion]
---
```

- Set `author: ai` in frontmatter for every note you create; switch to `author: mixed` when substantially rewriting a human-authored note. Authorship lives in frontmatter only — never add visible badges.
Save beside the PDF, link relevant existing Wiki concepts when appropriate, and use `do.obsidian-open` to present the result. Failure to open the desktop app does not invalidate the conversion.
