---
name: do.translate-markdown
description: |
  Translate Markdown documents to a target language with guaranteed completeness. Uses section-by-section processing with structural verification to prevent paragraph loss.
  Triggers: "translate markdown", "translate this md", "translate note", "translate to Chinese/English/Japanese"
---

# Translate Markdown (Completeness-Guaranteed)

Translate Markdown documents while ensuring **zero paragraph loss**, **perfect structure preservation**, and **consistent terminology**. Uses the same checklist-driven approach as `do.pdf-to-markdown`.

## 🚫 CRITICAL ANTI-PATTERNS (DO NOT DO THIS)
- **DO NOT** translate the entire document in a single pass. Long documents WILL have paragraphs silently dropped.
- **DO NOT** modify the original file. Always write to a new output file.
- **DO NOT** translate content inside code blocks, LaTeX math, wikilinks, or URLs.

---

## Workflow

### Phase 0: Determine Target Language

1. Check if the user specified a target language. If not, read `deeporbit.json` from the workspace root and use its `language` field.
2. Confirm with the user: "Translating `<filename>` to `<language>`. Proceed?"

---

### Phase 1: Structural Reconnaissance & Glossary Extraction

Before translating anything, you MUST read the **entire document** to build a glossary and structural map.

1. **Read the FULL source Markdown end-to-end.** This is NOT optional. You must understand the full context, writing style, and key terminology before translating a single word.

2. **Extract a Terminology Glossary** — identify ALL key terms, proper nouns, and recurring phrases. Decide their correct translation NOW so every section uses the same terms later:

```markdown
## Terminology Glossary

| Source Term | Translation | Notes |
|-------------|-------------|-------|
| Knowledge Base | 知识库 | Not "知识基地" |
| Agent | Agent | Keep English |
| Vault | 知识库 | Obsidian context |
| Wikilink | 双链 | |
| Completeness Verification | 完整性验证 | |
| ... | ... | Add 15-30 key terms |
```

> [!IMPORTANT]
> The glossary is the **single source of truth** for terminology. Every Ralph iteration MUST re-read the glossary before translating its section. This is how consistency is maintained across fresh context windows.

3. **Build the Structure Manifest** — create a checklist of every section:

```markdown
## Translation Manifest: <filename>

- Source: <filename>.md (<word count> words, <line count> lines)
- Target language: <language>
- Sections discovered:
  - [ ] Frontmatter/YAML (preserve as-is or translate values only)
  - [ ] # Section 1: Title (lines 1-25)
  - [ ] ## Section 1.1: Subtitle (lines 26-50)
  - [ ] ## Section 1.2: ... (lines 51-80)
  - [ ] ...
  - [ ] # Section N: References (lines X-Y)
- Code blocks: C (preserve untranslated)
- Tables: T (translate content, preserve structure)
- Math blocks: M (preserve untranslated)
- Wikilinks: W (preserve untranslated)
- Estimated output: ~<word count> words
```

4. **Save the manifest** (including the glossary at the top) as `<filename>_translation_manifest.md` alongside the source file. **Do not proceed to Phase 2 until this file is written.**

---

### Phase 2: Section-by-Section Translation (via Ralph Loop)

**CRITICAL: Each section is translated in a separate Ralph iteration. Do NOT attempt to translate multiple sections in one agent turn.**

**Step 1:** After Phase 0 + Phase 1 are done (language confirmed, manifest + glossary written), launch the Ralph loop:

```bash
/ralph:loop "You are running do.translate-markdown Phase 2. The manifest is at '<filename>_translation_manifest.md'. Target language: <language>. Your job in THIS iteration: 1) Read the manifest and glossary at the top. 2) Find the FIRST section still marked '- [ ]'. 3) Read that section from the source file. 4) Translate following preservation rules (DO NOT translate code blocks, math, wikilink targets, URLs). Use glossary for terminology. 5) APPEND to '<output_filename>.md'. 6) Update manifest: '- [ ]' to '- [x]'. 7) If ALL sections are now [x], run Phase 3 verification and output '<promise>TRANSLATION_COMPLETE</promise>'. Otherwise, just finish this turn." --completion-promise "TRANSLATION_COMPLETE" --max-iterations 30
```

**Step 2:** Each Ralph iteration does the following for ONE section:

1. **READ** the manifest → re-read the **glossary** first, then find the first unchecked `[ ]` section.
2. **READ** that section's line range from the source file.
3. **TRANSLATE** the content, following these preservation rules:

#### MUST Translate
- Headings (text only, keep `#` level)
- Paragraph text
- List item text
- Table cell content
- Callout/blockquote text
- Image alt text and captions
- Frontmatter `title`, `description`, `summary` values

#### MUST NOT Translate (Preserve Exactly)
- Code blocks (``` ... ```) — keep all code untouched
- Inline code (`` ` ... ` ``) — keep untouched
- LaTeX math (`$...$` and `$$...$$`)
- Wikilinks (`[[...]]`) — keep link targets, may translate display text `[[target|显示文本]]`
- URLs and external links — keep URLs, translate display text `[显示文本](url)`
- YAML frontmatter keys (translate values only)
- HTML tags
- Mermaid diagram node IDs (translate label text only)
- File paths and filenames
- Obsidian properties/tags (keep as-is unless user specifies)

4. **APPEND** the translated section to the output file immediately.
5. **CHECK OFF** the section in the manifest: `- [ ]` → `- [x]`.
6. **CONSISTENCY CHECK**: Verify all glossary terms in this section match the glossary.
7. **End the turn.** Ralph automatically starts the next iteration.

```mermaid
flowchart TD
    A["Phase 1 done: manifest + glossary"] --> B["/ralph:loop"]
    B --> C["Iteration N: Read glossary + manifest"]
    C --> D{"Find next [ ] section"}
    D -->|Found| E["Read source section"]
    E --> F["Translate using glossary"]
    F --> G["Append to output + check off [x]"]
    G --> H["Turn ends"]
    H --> C
    D -->|All [x]| I["Phase 3: Verification"]
    I --> J["TRANSLATION_COMPLETE"]
```

> [!IMPORTANT]
> Set `--max-iterations` to roughly 2× the number of sections. If Ralph stops mid-way, just re-run — it picks up from the first unchecked `[ ]`.

**Only after all sections are `[x]` does the loop proceed to Phase 3.**

---

### Phase 3: Completeness Verification

After all sections are translated:

1. **Manifest check**: Every `[ ]` must be `[x]`. If any remain, go back and translate them.

2. **Line count comparison**:
   - Source lines: S
   - Output lines: O
   - Ratio O/S should be between 0.8 and 1.3 (CJK translations are often shorter in lines but longer in characters)
   - If O/S < 0.6, sections were likely dropped — investigate

3. **Heading structure check**: Extract all headings from source and output. They must be 1:1 matching (same count, same hierarchy).

4. **Code block preservation check**: Count code blocks in source vs output — must be identical.

5. **Link preservation check**: Count wikilinks `[[...]]` and URLs in source vs output — must be identical.

6. **Report** results:

```markdown
## Translation Report

- Source: <filename>.md (<S> lines, <W> words)
- Output: <filename>_<LANG>.md (<O> lines, <W'> words)
- Target language: <language>
- Sections: <M>/<M> translated ✅
- Headings: <H>/<H> matched ✅
- Code blocks: <C>/<C> preserved ✅
- Wikilinks: <L>/<L> preserved ✅
- Terminology consistency: verified ✅
```

---

### Phase 4: Output & Cleanup

1. **Output file naming**: `<filename>_<LANG>.md`
   - Examples: `README_CN.md`, `research_EN.md`, `notes_JA.md`
   - Language codes: `CN` (Chinese), `EN` (English), `JA` (Japanese), `KO` (Korean), `FR` (French), `DE` (German), `ES` (Spanish)

2. **Frontmatter**: Update the output file's frontmatter:
```yaml
---
title: "<Translated Title>"
source: "[[<original filename>]]"
language: "<target language code>"
translated: YYYY-MM-DD
tags: [translation]
---
```

3. **Delete the manifest** file (or keep for audit).

---

## Handling Special Cases

### Markdown Tables
Translate cell content but preserve the table structure exactly:
```markdown
| Source | Target |      →      | 源文本 | 目标语言 |
|--------|--------|              |--------|----------|
| Hello  | World  |      →      | 你好   | 世界     |
```

### Mermaid Diagrams
- Translate **label text** inside node brackets: `A["Start"]` → `A["开始"]`
- **DO NOT** translate node IDs, direction keywords (`TD`, `LR`), or syntax keywords
- **DO NOT** use full-width punctuation inside Mermaid code blocks

### Callouts
Translate the content, preserve the type:
```markdown
> [!NOTE]                    →     > [!NOTE]
> This is important.         →     > 这很重要。
```

### Frontmatter with Wikilinks
```yaml
# Source                          # Translated
related: "[[Some Note]]"    →    related: "[[Some Note]]"  # keep link target
title: "My Research"        →    title: "我的研究"          # translate value
```

### Mixed-Language Content
If the source already contains mixed languages (e.g., English terms in a Chinese doc), preserve the untranslated terms unless user specifies otherwise. Technical terms, brand names, and proper nouns often stay in their original language.

---

## Translation Quality Standards

| Criterion | Requirement |
|-----------|-------------|
| Completeness | Every paragraph in source must appear in output |
| Structure | Heading hierarchy must be identical |
| Terminology | Consistent glossary terms throughout |
| Code integrity | All code blocks byte-identical to source |
| Link integrity | All wikilinks and URLs preserved |
| Natural language | Translation reads naturally, not machine-translated |
| No hallucination | Output contains ONLY content from the source |

---

## Ralph Loop Reference

| Ralph Feature | How Translate-Markdown Uses It |
|---|---|
| **Persistent state via files** | Manifest + glossary track progress and terminology across turns |
| **Fresh context each turn** | Each section gets full context window — no translation drift |
| **Completion promise** | `TRANSLATION_COMPLETE` triggers when all `[ ]` become `[x]` |
| **Max iterations safety** | Prevents infinite loops if a section fails repeatedly |
| **Self-correction** | Each turn re-reads glossary — terminology stays consistent |

## Rules

- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**
