# Architecture

DeepOrbit separates authoritative knowledge from derived runtime state.

## Portable core

Markdown notes, Properties, wikilinks, workflow checkpoints, templates, Bases, and `deeporbit.json` are authoritative. Every supported agent can read these artifacts without a proprietary database.

## Naming boundary

Keep **DeepOrbit** as the product, repository, executable, and public name. Use
the short `do.*` namespace only for Skills and slash commands: it is memorable,
groups commands together, and avoids claiming the generic `do` shell command.

## Deterministic core

The `deeporbit` Python package performs operations where exactness matters: initialization, migrations, task IDs, task completion, calendar serialization, index reconciliation, locking, and structured diagnostics. The base package uses only the Python standard library.

## Capability adapters

Skills express intent and workflow. Runtime packages register native commands, MCP, hooks, goals, or trackers. An adapter can disappear without losing knowledge or progress because it never owns authoritative state.

## Derived retrieval state

Indexes are caches stored outside the vault. The manifest records file size, nanosecond mtime, and SHA-256. The current vault file set controls deletion. Semantic chunk IDs include relative path, file hash, and ordinal, so identical paragraphs in different notes do not collide.

## Failure model

- Missing semantic dependencies: lexical retrieval continues.
- Missing Obsidian CLI: URI and path fallbacks continue.
- Missing community plugins: Markdown and Python operations continue.
- Hook failure: retrieval still checks freshness before query.
- Interrupted long workflow: the Markdown checkpoint resumes.
- Sync conflict: retain both versions and require a user-reviewed merge.
