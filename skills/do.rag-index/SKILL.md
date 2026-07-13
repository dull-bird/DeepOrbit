---
name: do.rag-index
description: Build, refresh, inspect, or repair DeepOrbit's machine-local search indexes. Use when notes were synced or moved, retrieval is stale, the user asks to rebuild RAG, or DeepOrbit reports an index problem.
---

# Maintain the Local Index

Run one of:

```bash
deeporbit --vault "<vault>" index status
deeporbit --vault "<vault>" index ensure
deeporbit --vault "<vault>" index ensure --semantic
```

The lexical SQLite index is always available and stored outside the vault in the OS cache directory. `--semantic` updates optional ChromaDB and may download an embedding model on first use.

Never commit or synchronize an index. Git and Obsidian Sync carry Markdown and `deeporbit.json`; each device safely rebuilds its own cache. Report added, updated, deleted, and unchanged counts.
