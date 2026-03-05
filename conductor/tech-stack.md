# Tech Stack

## Core Platform
- **Gemini CLI / Claude Code Extension**: The primary execution environment for AI agent skills and commands.
- **Obsidian**: The target storage and visualization layer for the personal knowledge vault.

## Languages & Configuration
- **Python (3.10+)**: Used for backend scripts (e.g., `fix_links.py`, `extract_texts.py`, `marker_to_markdown.py`) and complex data processing.
- **TOML**: Configuration format for defining CLI commands (`commands/*.toml`).
- **Markdown (Gfm)**: Primary format for skill definitions (`skills/*/SKILL.md`) and project documentation.

## Specialized Tools & Libraries
- **Playwright**: Used for browser automation and RAG-based queries in `notebooklm`.
- **marker-pdf**: High-fidelity OCR and PDF-to-Markdown conversion for academic papers.
- **xeLaTeX**: Used by `arxiv-translator` to compile translated LaTeX sources into Chinese PDFs.

## Integration & Communication
- **Tool-Call Protocol**: Standardized interface for Gemini CLI to interact with the local filesystem and external APIs.
- **Mermaid.js**: Used for visualizing knowledge maps and system architectures within the Obsidian vault.
- **WikiLinks (`[[NoteName]]`)**: The primary mechanism for cross-referencing and building the knowledge graph.

## Development Environment
- **git**: Source control and project state management.
- **Obsidian Plugins**: Optional (e.g., Dataview, Periodic Notes) for advanced vault functionality.
