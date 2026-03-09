---
name: do.fix-links
description: Automatically scans wiki links in 40_Wiki, identifies missing note files, and automatically completes them. Includes: 1. Automatic creation of missing files; 2. Deep content filling (Wiki + First Principles); 3. Intelligent automatic classification.
---

# Ghost Link Fixer & Filler (Pro)

## Overview

This skill ensures the DeepOrbit knowledge base remains coherent, in-depth, and well-organized. It not only fills gaps but also provides insights through deep decomposition.

## Workflow

1.  **Identify & Create**: Run `scripts/fix_links.py` to identify missing links and generate placeholder files (located in `40_Wiki/未分类/`).
2.  **深度填充 (Deep Filling)**:
    -   Obtain a list of newly created entries.
    -   Call `google_web_search` to search for core definitions, background, and underlying logic.
    -   **Content Generation Guidelines**:
        -   **Style**: Wikipedia-style (objective, structured, high signal-to-noise ratio).
        -   **Depth**: Must include a **"First Principles Decomposition"** (First Principles) section, unearthing the concept's essential assumptions, core contradictions, or physical/mathematical foundations.
        -   **Structure**: Definition -> First Principles/Underlying Logic -> Key Points -> Applications/Examples -> Related Concepts.
    -   **Execute Move & Write**: Use `write_file` to populate content and move it to the target subdirectory (intelligent classification).

## Usage

Enter `/do:fix-links` directly in the command line.

## Notes

-   When filling content, be sure to preserve Frontmatter such as `area` and `tags`.
-   First Principles decomposition should avoid clichés and pursue unique insights.

## Rules

- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**

