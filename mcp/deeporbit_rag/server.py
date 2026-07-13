#!/usr/bin/env python3
"""Runtime-neutral MCP facade for the DeepOrbit local core."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from deeporbit.config import load_config  # noqa: E402
from deeporbit.doctor import diagnose  # noqa: E402
from deeporbit.search import SearchIndex  # noqa: E402
from deeporbit.semantic import ChromaIndex  # noqa: E402
from deeporbit.tasks import agenda  # noqa: E402

mcp = FastMCP("deeporbit")


def _config(vault_path: str | None):
    return load_config(vault_path or os.environ.get("DEEPORBIT_VAULT") or os.getcwd())


@mcp.tool()
def deeporbit_status(vault_path: str | None = None) -> str:
    """Report vault, local index, optional plugin, and runtime capabilities."""
    return json.dumps(diagnose(_config(vault_path)), ensure_ascii=False, indent=2)


@mcp.tool()
def rag_search(query: str, top_k: int = 10, vault_path: str | None = None) -> str:
    """Zero-dependency lexical retrieval across the configured vault folders."""
    results = SearchIndex(_config(vault_path)).query(query, limit=top_k)
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def rag_query(query: str, top_k: int = 5, vault_path: str | None = None, semantic: bool = True) -> str:
    """Hybrid retrieval; uses optional Chroma semantics and always retains lexical fallback."""
    config = _config(vault_path)
    index = SearchIndex(config)
    results = index.query(query, limit=top_k)
    if semantic and ChromaIndex.available():
        semantic_index = ChromaIndex(config)
        semantic_index.ensure(index.file_manifest())
        seen = {item["path"] for item in results}
        results.extend(item for item in semantic_index.query(query, limit=top_k) if item["path"] not in seen)
    return json.dumps(results[:top_k], ensure_ascii=False, indent=2)


@mcp.tool()
def task_agenda(vault_path: str | None = None) -> str:
    """Read active Markdown tasks grouped into overdue, today, upcoming, and unscheduled."""
    grouped = agenda(_config(vault_path))
    return json.dumps({key: [asdict(task) for task in tasks] for key, tasks in grouped.items()}, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
