---
name: do.translate
description: "Translate documents smartly. Accepts a URL or a PDF file as input. Detects if it is an arXiv URL or paper. If yes, runs do.arxiv-translator. If it is a standard PDF, runs do.pdf-to-markdown followed by do.translate-markdown."
---

# Translate (Smart Router)

This skill acts as a smart router for translation requests, automatically detecting the input type and invoking the correct specialized skills.

## Workflow

### 1. Identify Input Type
- Extract the input from the user's request (e.g., an arXiv URL, a web URL, or a local PDF file path).
- Determine if the input is an arXiv paper. Examples:
  - The URL contains `arxiv.org`.
  - The URL contains `arxiv:` followed by an ID.
  - The file is a PDF downloaded from arXiv.

### 2. Route to Specialized Skill
- **If arXiv Paper:**
  - Execute the `do.arxiv-translator` skill on the input. This is optimal for arXiv papers as it compiles LaTeX source directly.
- **If Standard PDF (Non-arXiv):**
  - Step 2.1: Execute the `do.pdf-to-markdown` skill on the PDF to convert it to high-fidelity Markdown. Wait for the conversion checklist and promises to complete.
  - Step 2.2: Execute the `do.translate-markdown` skill on the resulting Markdown file to translate it into the target language.

### 3. Archive & Standardize Output
- After the PDF translation process is complete, you **MUST** move the final translated Markdown document (`.md`) and any extracted assets (like images) into the vault's paper directory: `60_Notes/papers/<Paper_Title>/`.
- Ensure the file naming is standardized, such as `60_Notes/papers/<Paper_Title>/<Paper_Title>_<LANG>.md` (e.g. `60_Notes/papers/Attention Is All You Need/Attention Is All You Need_CN.md`).
*(Note: If routed to `do.arxiv-translator`, it handles its own `.pdf` archiving internally).*

## Guidelines
- Do not process the translation natively inside this skill. This is only a routing step.
- Ensure you wait for `do.pdf-to-markdown` to completely finish before triggering `do.translate-markdown`.

## Rules
- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**
