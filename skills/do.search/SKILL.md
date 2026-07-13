---
name: do.search
description: Perform fast lexical, filename, property, or phrase search across a DeepOrbit vault. Use for exact names, identifiers, tags, error text, regex-like lookup intent, or when semantic retrieval is unnecessary or unavailable.
---

# Search the Vault

Run:

```bash
deeporbit --vault "<vault>" rag "<query>" --limit 20
```

This uses the zero-dependency local SQLite FTS index and automatically reconciles synced, changed, renamed, and deleted Markdown files. If SQLite FTS is unavailable, the core falls back to direct case-insensitive scanning.

Return vault-relative paths, note titles, and short snippets. Do not modify notes during search.
