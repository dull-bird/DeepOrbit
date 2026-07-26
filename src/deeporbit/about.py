"""Query and edit vault directory semantics (`deeporbit about`)."""

from __future__ import annotations

from .config import Config, DIRECTORY_META


def _node(cfg: Config, logical_name: str, meta: dict, parent: str | None = None) -> dict:
    path = meta.get("path")
    if not path and parent is None:
        path = cfg.directories.get(logical_name)
    return {
        "logical_name": logical_name,
        "path": path,
        "title": meta.get("title", ""),
        "summary": meta.get("summary", ""),
        "when_not": meta.get("when_not", ""),
        "ai_notes": meta.get("ai_notes", ""),
        "custom": bool(meta.get("custom", False)),
        "parent": parent,
        "children": [
            _node(cfg, child_name, child_meta, parent=logical_name)
            for child_name, child_meta in (meta.get("children") or {}).items()
        ],
    }


def tree(cfg: Config) -> list[dict]:
    """All top-level nodes with their children, ordered by path."""
    nodes = []
    for logical_name in cfg.directories:
        meta = cfg.directory_meta.get(logical_name) or {}
        nodes.append(_node(cfg, logical_name, meta))
    nodes.sort(key=lambda n: n.get("path") or "")
    return nodes


def flatten(cfg: Config) -> list[dict]:
    """All nodes including nested children, as a flat list."""
    out: list[dict] = []

    def walk(node: dict) -> None:
        out.append({k: v for k, v in node.items() if k != "children"})
        for child in node["children"]:
            walk(child)

    for top in tree(cfg):
        walk(top)
    return out


def lookup(cfg: Config, key: str) -> dict:
    """Find one node by logical name, path, or title."""
    needle = key.strip()
    for node in flatten(cfg):
        if needle in (node["logical_name"], node["path"], node["title"]):
            return node
    raise KeyError(f"Unknown directory: {key!r}")
