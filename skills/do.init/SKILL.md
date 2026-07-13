---
name: do.init
description: Initialize or safely upgrade a DeepOrbit Obsidian vault. Use when the user asks to set up DeepOrbit, create the vault folders, migrate legacy Chinese folder names, repair a partial installation, or generate deeporbit.json.
---

# Initialize DeepOrbit

Run the deterministic initializer from the repository or installed Python package:

```bash
deeporbit --vault "<vault-path>" init
```

If the `deeporbit` executable is unavailable, run `PYTHONPATH=<repo>/src python -m deeporbit --vault "<vault-path>" init`.

The command is idempotent. It creates missing folders, including `15_Writings`, preserves existing notes, merges legacy localized folders only when safe, and reports conflicting files without overwriting either copy.

After initialization:

1. Read the JSON result.
2. If `conflicts` is non-empty, show every path and ask the user how to merge it; do not delete either file.
3. Run `deeporbit --vault "<vault-path>" doctor`.
4. Explain which optional capabilities are available. Missing Obsidian CLI, ChromaDB, Tasks, Dataview, or Calendar must not be treated as initialization failures.
