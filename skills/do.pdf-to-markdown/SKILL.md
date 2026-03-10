---
name: do.pdf-to-markdown
description: |
  Convert PDF documents to high-fidelity Markdown with guaranteed completeness. Uses page-by-page sequential processing with structural verification to prevent paragraph loss.
  Triggers: "PDF to markdown", "convert PDF", "extract PDF text", "PDF to md", "read this PDF"
---

# PDF to Markdown (Completeness-Guaranteed)

Convert PDF documents into structured Markdown while ensuring **zero paragraph loss** and **perfect formula/table preservation**. This skill uses a rigorous multi-pass workflow: first build a structural map of the entire document, then convert page-by-page with continuous verification.

## 🚫 CRITICAL ANTI-PATTERNS (DO NOT DO THIS)
- **DO NOT** write or run Python scripts (e.g., `PyMuPDF`, `fitz.get_text()`, `pdfplumber`) to blindly extract text. Python text extraction destroys LaTeX math formulas, breaks tables, and ruins multi-column layouts.
- **DO NOT** try to convert the entire document in one single turn.
- **YOU MUST** use your native multimodal vision capabilities by calling the `read_file` tool directly on the PDF. This passes the PDF to you visually, allowing you to correctly perceive and transcribe LaTeX math, tables, and complex layouts.

## Prerequisites

```bash
pip install pdfplumber
```
*(pdfplumber is ONLY for the `extract_images_pdfplumber.py` script, NOT for text extraction!)*

---

## Workflow

### Phase 1: Structural Reconnaissance

Before converting any content, you MUST build a complete map of the document.

1. **Read the PDF** using the `read_file` tool to visually inspect the document and get a global overview.
2. **Extract the Structure Manifest** — YOU MUST physically create a checklist file of every structural element.

```markdown
## Structure Manifest: <filename>

- Total pages: N
- Sections discovered:
  - [ ] Title / Cover Page (p.1)
  - [ ] Abstract (p.1-2)
  - [ ] Section 1: Introduction (p.2-4)
  - [ ] Section 2: Related Work (p.4-7)
  - [ ] ...
  - [ ] References (p.N-1 - N)
  - [ ] Appendix (p.N)
- Tables: T (list page numbers)
- Figures: F (list page numbers)
- Footnotes: estimated count
```

3. **Save this manifest** as `<filename>_manifest.md` in the same directory as the PDF. This is your **completeness checklist** — every item must be checked off by the end. **Do not proceed to Phase 2 until this file is written.**

> [!IMPORTANT]
> If the PDF has a Table of Contents, use it as the primary source for the manifest. If not, scan page-by-page headers to build one.

4. **Extract all images** from the PDF using the built-in script:

```bash
python {skill_path}/scripts/extract_images_pdfplumber.py <input.pdf>
```

This will:
- Create a `<filename>_assets/` directory alongside the PDF
- Save every embedded image (PNG/JPEG) with page-aware naming: `page3_img1.png`
- Print a Markdown manifest of all extracted images

Note the image count in the manifest — it will be verified in Phase 3.

---

### Phase 2: Page-by-Page Sequential Conversion

**CRITICAL: Process ONE page range at a time. Use `read_file` with `start_line` / `end_line` (or visually read specific pages). Do NOT attempt to convert the entire document in a single pass.**

For each section in the manifest:

1. **READ** the specific page visually using `read_file`.
2. **CONVERT** to Markdown manually, preserving:
   - Heading hierarchy (`#`, `##`, `###`)
   - Paragraph breaks (empty lines between paragraphs)
   - Bold/italic emphasis
   - Bullet and numbered lists
   - Tables → Markdown tables
   - Math formulas → LaTeX (`$inline$` or `$$block$$`). **You must visually transcribe the math into LaTeX.**
   - Code blocks → fenced code blocks with language
   - Footnotes → Markdown footnotes `[^1]`
   - Figure references → `![Figure N: caption](<filename>_assets/pageX_imgY.ext)` using extracted images
3. **APPEND** to the output file `<filename>.md` immediately (do not hold everything in memory).
4. **CHECK OFF** the section in the manifest: `- [ ]` → `- [x]` by updating `<filename>_manifest.md`.
5. **VERIFY** the converted section:
   - Does the paragraph count roughly match the source?
   - Are there any obvious truncations (sentences ending mid-thought)?
   - Are all tables from this page range present?

**Only then proceed to the next section.**

---

### Phase 3: Completeness Verification

After all sections are converted, run a final verification pass:

1. **Manifest check**: Open the manifest — every `[ ]` must now be `[x]`. If any remain unchecked, go back and convert those sections.

2. **Page coverage check**: Verify that every page of the PDF is accounted for.

3. **Section boundary check**: Ensure no section headers from the manifest are missing in the output. Search the output for each section title.

4. **Table/Figure count**: Verify the number of tables and figures matches the manifest counts.

5. **Report** the verification results:

```markdown
## Conversion Report

- Source: <filename>.pdf (<N> pages)
- Output: <filename>.md (<word count> words)
- Sections: <M>/<M> verified ✅
- Tables: <T>/<T> converted ✅
- Figures: <F>/<F> extracted ✅
- Images saved to: `<filename>_assets/` (<count> files)
- Estimated completeness: ~XX%
```

---

### Phase 4: Output & Cleanup

1. **Final output** path: save alongside the PDF as `<filename>.md`
2. **Frontmatter**:

```yaml
---
type: note
title: "<Document Title>"
source: "[[<filename>.pdf]]"
created: YYYY-MM-DD
tags: [pdf-conversion]
---
```

3. **Delete the manifest** file (or keep if user wants it for audit)
4. **Link** key concepts with `[[wikilinks]]` to `40_Wiki` if applicable

---

## Handling Special Content

### Math Formulas
- Inline: `$E = mc^2$`
- Block: `$$\int_0^1 f(x)dx$$`
- Preserve LaTeX commands exactly as they appear

### Tables
- Convert to standard Markdown table syntax
- For complex merged-cell tables, use HTML `<table>` as fallback
- Always verify column count matches source

### Images & Figures
- **Run the extraction script first** (Phase 1, step 4) to get real image files in `<filename>_assets/`
- Reference extracted images in Markdown: `![Figure 3: Architecture overview](paper_assets/page5_img1.png)`

### Multi-Column Layouts
- Linearize to single-column, preserving reading order (left column first, then right)

## Rules

- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**
