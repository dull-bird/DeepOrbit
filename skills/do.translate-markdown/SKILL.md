---
name: do.translate-markdown
description: Translate Markdown documents to a target language with checkpointed completeness, glossary consistency, and structural verification. Use when the user asks to translate Markdown, notes, documentation, or long structured text while preserving code, links, math, wikilinks, and formatting.
---

# Translate Markdown

Write a new output file; never overwrite the source. Preserve code, math, URLs, wikilink targets, and Markdown structure.

## 1. Set language and inspect the source

Use the user's explicit target language. Otherwise read `deeporbit.json` and confirm the configured language. Read the full source before translating.

Create `<name>_translation_manifest.md`:

```markdown
---
deeporbit_workflow: 1
workflow_id: translate-<date>-<slug>
status: active
source: <name>.md
output: <name>_<LANG>.md
---

# Terminology Glossary
| Source | Translation | Notes |
|---|---|---|

# Section Checklist
- [ ] Frontmatter and title
- [ ] Section 1
- [ ] Section 2
- [ ] Footnotes and references
```

Capture recurring terminology, proper nouns, and intentional untranslated terms before translating prose.

## 2. Translate with checkpoints

For each unchecked section:

1. Reread the glossary and relevant source context.
2. Translate into natural target-language prose.
3. Preserve heading levels, paragraph count, list nesting, tables, callout types, link destinations, code, and math.
4. In Mermaid blocks, translate labels only; preserve IDs and syntax.
5. Compare source and output section structure.
6. Mark the section checked only after verification.

Continue while context allows. If interrupted, resume from the first unchecked item. Runtime Goals and Trackers may mirror the objective but never replace the manifest. Do not use an external self-invoking loop.

## 3. Final verification

- Every source paragraph has an output counterpart.
- Heading hierarchy and list structure match.
- Glossary terms are consistent.
- Code blocks, formulas, URLs, and wikilink targets are unchanged.
- No new claims or explanations were introduced.

- Set `author: ai` in frontmatter for every note you create; switch to `author: mixed` when substantially rewriting a human-authored note. Authorship lives in frontmatter only — never add visible badges.
Write output as `<name>_<LANG>.md` with translated title, source wikilink, language, translation date, and `translation` tag. Keep the manifest for audit unless the user requests cleanup. Open the output through `do.obsidian-open`; opening failure is non-fatal.
