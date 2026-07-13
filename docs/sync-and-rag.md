# Sync and rebuild RAG

Use this guide when moving a vault between computers or choosing Git versus Obsidian Sync.

## What to sync

Sync the entire vault, including `deeporbit.json`, Markdown, `.base` files, templates, attachments, and optional ICS exports. Do not sync the machine cache under `~/.cache/deeporbit` (Linux), the equivalent macOS cache, or `%LOCALAPPDATA%\deeporbit` on Windows.

## Git

Commit the vault's human-readable files. Pull before starting a session and resolve Markdown conflicts before asking an agent to reorganize or complete tasks. DeepOrbit does not automatically commit or push.

## Obsidian Sync

Wait for Obsidian's sync indicator to settle before a large write operation. DeepOrbit sees downloaded notes as ordinary filesystem changes. Version history remains the recovery mechanism for accidental edits.

## First query on another computer

```bash
deeporbit --vault /path/to/vault doctor
deeporbit --vault /path/to/vault index ensure
deeporbit --vault /path/to/vault rag "test query"
```

`index ensure` reconciles new, changed, renamed, and deleted notes. It is safe to repeat.

## Semantic retrieval

```bash
python3 -m pip install 'deeporbit[rag]'
deeporbit --vault /path/to/vault index ensure --semantic
```

Each computer downloads its own embedding model and builds its own Chroma cache. Rebuild when the embedding model or index version changes.
