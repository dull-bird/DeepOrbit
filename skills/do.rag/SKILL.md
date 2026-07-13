---
name: do.rag
description: Retrieve relevant context from a DeepOrbit Obsidian vault using self-refreshing local lexical search and optional semantic RAG. Use when answering from prior notes, recalling a project, finding related research, or grounding another DeepOrbit workflow.
---

# Retrieve Vault Context

Preferred order:

1. If the DeepOrbit MCP server is available, call `rag_query` or `rag_search`.
2. Otherwise run `deeporbit --vault "<vault>" rag "<query>"`.
3. Add `--semantic` only when ChromaDB is installed or the user asks for semantic retrieval.
4. If the CLI is unavailable, search Markdown directly and disclose the fallback.

Every query refreshes changed and deleted files before retrieval. Cite results with `[[Title]]` and their vault-relative paths. Distinguish retrieved facts from general knowledge and never invent note content.
