---
name: do.obsidian-open
description: Open or reveal Markdown notes in Obsidian with portable fallbacks. Use after creating or modifying a note, when the user asks to open a vault file, or when another DeepOrbit workflow needs to present its output.
---

# Open a Note

Use this priority order:

1. If the `obsidian` executable exists, run `obsidian open path="<absolute-path>"` without blocking the main workflow.
2. Otherwise open an encoded `obsidian://open?path=<absolute-path>` URI.
3. If neither is available, return the absolute path so the user can open it manually.

When the Python Core is installed, `deeporbit.openers.open_note()` implements this order. Never treat the inability to launch the desktop application as a failure of the file creation or knowledge workflow. Do not invent vault names or unencoded URIs.
