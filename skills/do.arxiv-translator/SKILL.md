---
name: do.arxiv-translator
description: "Automatically downloads LaTeX source from arXiv, translates it to a target language (default Chinese), and compiles it to PDF using xelatex. Uses modern xeCJK for multilingual support. Trigger when the user provides an arXiv URL, paper ID, or natural language query about an arXiv paper and wants it translated/compiled."
---

# arXiv LaTeX Translator & Compiler (Modern Solution)

This skill handles the end-to-end workflow of converting an arXiv paper's LaTeX source into a translated PDF on Windows, macOS, and Linux using modern `xeCJK` and `fontspec`.

## Workflow

### 0. Pre-flight Dependency Check
Before starting, verify that all required system tools are installed.
- **Windows (PowerShell):** `Get-Command curl, tar, xelatex, bibtex -ErrorAction SilentlyContinue`
- **macOS / Linux (Bash):** `for cmd in curl tar xelatex bibtex; do command -v $cmd >/dev/null 2>&1 || echo "Missing: $cmd"; done`

### 1. Identify & Download
- Extract the ID (e.g., `2508.11825v2`) from the URL or find it via search.
- Create a target directory and download/extract the source and the paper pdf (for final check) using native tools (`curl`, `tar`).
  - Abstract: `https://arxiv.org/abs/xxxx.xxxxx`
  - Source: `https://arxiv.org/src/xxxx.xxxxx`
  - PDF: `https://arxiv.org/pdf/xxxx.xxxxx.pdf`

### 2. Analyze & Modularize (For Large Papers)
- Read the original `.pdf` file to build a mental map.
- **Modularization Strategy (Crucial for Reliability):**
    - If the main `.tex` file is large (>500 lines), **DO NOT use the `replace` tool for content translation.** It is prone to whitespace/encoding mismatches.
    - Instead, write and run a Python script to split the monolithic `.tex` file into sub-files by `\section` (e.g., `sections/01_intro.tex`, `sections/02_related.tex`).
    - Update the main `.tex` file to use `\input{sections/xxx.tex}`.
    - For small files, you may still use `replace` or directly overwrite the file with `write_file`.
- **Terminology Glossary:** Create a local mental glossary of 5-10 core technical terms to ensure consistency.

### 3. Atomic Translation (Write-File Overwrite)
- **Work on Chunks:** Translate one sub-file (or one section) at a time.
- **Overwrite Mode:** Use the `write_file` tool to write the fully translated content into the sub-files. This avoids the "string not found" errors common with the `replace` tool.
- **Content Preservation:** Rigorously preserve LaTeX commands, math environments, citations, and references.
- **Modern Chinese Support (xeCJK)**:
    - Inject `\usepackage{xeCJK}` and `\setCJKmainfont{Microsoft YaHei}` (or platform equivalent) into the main preamble.

### 4. Compile & Auto-Fix
- Use `xelatex -interaction=nonstopmode`.
- **Standard compilation loop:** `xelatex` -> `bibtex` -> `xelatex` x2.
- **Error Auto-Fixing:** If compilation fails, read the `.log` file, identify the error line, and fix the corresponding sub-file using `write_file` or `replace`.

### 5. Integrity Verification & Review
- **Completeness Check:** Verify all sub-files in `sections/` are translated.
- **Visual Check:** Compare the translated PDF with the original.
- Clean up intermediate files and move the final `_CN.pdf` to the root.

## Guidelines
- **Prefer `write_file` over `replace` for Translation**: Overwriting a small, dedicated section file is 100% reliable compared to searching for a literal string in a 20,000-line file.
- **Font Selection**:
    - Windows: `Microsoft YaHei` or `SimSun`.
    - macOS: `PingFang SC`.
    - Linux: `Noto Sans CJK SC`.
- **Preserve Template**: Use `xeCJK` to minimize style interference.
- **Heredocs**: Use single-quoted heredocs in shells to handle backslashes correctly.

## Rules

- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**

