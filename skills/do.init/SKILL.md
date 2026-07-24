---
name: do.init
description: Initialize or safely upgrade a DeepOrbit Obsidian vault. Use when the user asks to set up DeepOrbit, create the vault folders, migrate legacy Chinese folder names, repair a partial installation, or generate deeporbit.json.
---

# Initialize DeepOrbit

Run the deterministic initializer from the installed CLI and point it at the
DeepOrbit repository checkout that should be materialized into the vault:

```bash
deeporbit --vault "<vault-path>" init --source "<deeporbit-repo-path>"
```

If the `deeporbit` executable is unavailable, run `PYTHONPATH=<repo>/src python -m deeporbit --vault "<vault-path>" init --source "<repo>"`.

The command is idempotent. It creates missing folders, including `15_Writings`, preserves existing notes, merges legacy localized folders only when safe, and reports conflicting files without overwriting either copy.

Initialization materializes the workflow skills into `99_System/DeepOrbit/skills/`, writes `99_System/DeepOrbit/skills-index.json`, overlays missing system templates/prompts/Bases, refreshes mentor guides, and copies a curated runtime bundle into `99_System/DeepOrbit/repo/`. The bundle is the project-level handoff surface: it includes skills, commands, prompts, hooks, CLI source, MCP, docs, and manifests, but excludes `.git`, virtualenvs, caches, build outputs, `node_modules`, and generated agent install directories.

External workspaces should install only the global `do.link` connector; after `init`, the vault itself carries the workflow catalog needed for routing.

After initialization:

1. Read the JSON result.
2. If `conflicts` is non-empty, show every path and ask the user how to merge it; do not delete either file.
3. Run `deeporbit --vault "<vault-path>" doctor`.
4. Explain which optional capabilities are available. Missing Obsidian CLI, ChromaDB, Tasks, Dataview, or Calendar must not be treated as initialization failures.
