#!/usr/bin/env python3
"""DeepOrbit RAG MCP server.

Exposes the DeepOrbit vault's retrieval capabilities as native MCP tools so any
MCP-capable agent (Claude Code, etc.) can call them directly instead of shelling
out to the CLI scripts in `scripts/rag/`:

  - rag_query:  semantic search over the ChromaDB index (built by /do:rag-index)
  - rag_search: exact string / regex search across vault note directories

The vault path is resolved from (in order): the tool's `vault_path` argument, the
DEEPORBIT_VAULT environment variable, then the current working directory.

Run standalone:  DEEPORBIT_VAULT=/path/to/vault python3 server.py
Dependencies:    pip install -r requirements.txt
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("deeporbit-rag")

# Note directories scanned by the exact/regex search (mirrors scripts/rag/search_vault.py)
TARGET_DIRS = [
    "10_Diary",
    "20_Projects",
    "30_Research",
    "40_Wiki",
    "50_Resources",
    "60_Notes",
]

COLLECTION_NAME = "deeporbit_notes"


def _resolve_vault(vault_path: str | None) -> Path:
    raw = vault_path or os.environ.get("DEEPORBIT_VAULT") or os.getcwd()
    p = Path(raw).expanduser().resolve()
    if not p.is_dir():
        raise ValueError(
            f"Vault path '{p}' does not exist. Pass vault_path or set DEEPORBIT_VAULT."
        )
    return p


@mcp.tool()
def rag_query(query: str, top_k: int = 5, vault_path: str | None = None) -> str:
    """Semantic (vector) search over the DeepOrbit vault.

    Requires the ChromaDB index built by the do.rag-index skill (`/do:rag-index`).
    Returns the most relevant note chunks as Markdown with wikilink-friendly titles.

    Args:
        query: Natural-language question or topic to retrieve context for.
        top_k: Number of chunks to return (default 5).
        vault_path: Optional absolute path to the vault; overrides DEEPORBIT_VAULT.
    """
    import chromadb
    from chromadb.utils import embedding_functions

    vault = _resolve_vault(vault_path)
    db_path = vault / ".deeporbit" / "chromadb"
    if not db_path.exists():
        return (
            "Error: ChromaDB index not found. Build it first with the do.rag-index "
            "skill (`/do:rag-index`)."
        )

    try:
        client = chromadb.PersistentClient(path=str(db_path))
        emb_fn = embedding_functions.DefaultEmbeddingFunction()
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=emb_fn)
    except Exception as exc:  # noqa: BLE001
        return f"Failed to load ChromaDB index: {exc}"

    results = collection.query(query_texts=[query], n_results=max(1, top_k))
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return "No relevant notes found in the vault."

    out = ["### RAG Context Retrieved from Vault\n"]
    for doc, meta in zip(documents, metadatas):
        title = meta.get("title", "Unknown")
        file_path = meta.get("file_path", "Unknown")
        out.append(f"**From Note: [[{title}]]** (Path: `{file_path}`)")
        out.append(f"```text\n{doc}\n```\n")
    return "\n".join(out)


@mcp.tool()
def rag_search(query: str, case_sensitive: bool = False, vault_path: str | None = None) -> str:
    """Exact string / regex search across the DeepOrbit vault note directories.

    No index required — scans Markdown files directly. Use for precise keyword or
    pattern matching when semantic search is too fuzzy.

    Args:
        query: Exact string or Python regex pattern.
        case_sensitive: Match case exactly (default False).
        vault_path: Optional absolute path to the vault; overrides DEEPORBIT_VAULT.
    """
    vault = _resolve_vault(vault_path)
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(query, flags=flags)
    except re.error as exc:
        return f"Invalid regex pattern: {exc}"

    results: list[dict] = []
    for d in TARGET_DIRS:
        target = vault / d
        if not target.is_dir():
            continue
        for root, _, files in os.walk(target):
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                full = Path(root) / fname
                rel = str(full.relative_to(vault))
                try:
                    lines = full.read_text(encoding="utf-8").splitlines()
                except Exception:  # noqa: BLE001
                    continue
                matches = [
                    (i + 1, line.strip())
                    for i, line in enumerate(lines)
                    if pattern.search(line)
                ]
                if matches:
                    results.append({"file": rel, "title": full.stem, "matches": matches})

    if not results:
        return f"No exact matches found for: '{query}'"

    out = [f"### Exact Search Results for '{query}'\n"]
    for res in results:
        out.append(f"**From Note: [[{res['title']}]]** (Path: `{res['file']}`)")
        out.append("```text")
        for line_num, content in res["matches"]:
            if len(content) > 150:
                content = content[:150] + "..."
            out.append(f"L{line_num}: {content}")
        out.append("```\n")
    return "\n".join(out)


if __name__ == "__main__":
    mcp.run()
