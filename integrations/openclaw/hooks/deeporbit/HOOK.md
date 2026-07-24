---
name: deeporbit
description: "Inject DeepOrbit vault context on session start; mark index dirty on file changes"
homepage: https://github.com/dull-bird/DeepOrbit
metadata:
  {
    "openclaw":
      {
        "emoji": "🪐",
        "events": ["agent:bootstrap", "workspace:file-change"],
        "install": [{ "id": "bundled", "kind": "bundled", "label": "deeporbit" }],
      },
  }
---

# DeepOrbit Context Hook

Injects DeepOrbit vault context (prompt, profile, status) into the agent's
bootstrap on session start, and marks the local search index dirty when
workspace files change.

## Events

- `agent:bootstrap`: Reads `DeepOrbitPrompt.md` from the vault (or repo),
  appends vault status and profile fields, injects as bootstrap context.
- `workspace:file-change`: Touches `~/.cache/deeporbit/<vault>/dirty` so the
  next RAG query knows to re-index.

## Requirements

- Python 3.10+ with DeepOrbit installed (`pip install -e <repo>`) OR the
  `PYTHONPATH` fallback pointing to `<repo>/src`.
- A linked vault (via `deeporbit link add`) or `DEEPORBIT_VAULT` env var.

## Enable

```bash
openclaw hooks enable deeporbit
```
