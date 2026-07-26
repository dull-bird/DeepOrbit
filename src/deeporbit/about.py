"""Query and edit vault directory semantics (`deeporbit about`)."""

from __future__ import annotations

import json

from .config import CONFIG_NAME, DIRECTORIES, SCHEMA_VERSION, Config, DIRECTORY_META
from .errors import ConfigError


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


def _read_payload(cfg: Config) -> dict:
    path = cfg.vault / CONFIG_NAME
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_payload(cfg: Config, payload: dict) -> None:
    payload["schema_version"] = SCHEMA_VERSION
    (cfg.vault / CONFIG_NAME).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _user_overrides(cfg: Config) -> dict:
    """Extract only the fields the user explicitly set (differs from defaults)."""
    out: dict[str, dict] = {}
    for key, full in cfg.directories_full.items():
        default = DIRECTORY_META.get(key, {})
        entry: dict = {"path": full["path"]}
        for field_name in ("title", "summary", "when_not", "ai_notes", "custom"):
            value = full.get(field_name)
            if value is None:
                continue
            if field_name in default and default[field_name] == value:
                continue
            entry[field_name] = value
        out[key] = entry
    return out


def add(
    cfg: Config,
    *,
    logical_name: str,
    path: str,
    title: str,
    summary: str = "",
    when_not: str = "",
    ai_notes: str = "",
    parent: str | None = None,
) -> dict:
    if logical_name in cfg.directories and parent is None:
        raise ConfigError(
            f"Logical directory already exists: {logical_name!r} (use `about set` to modify)"
        )
    if parent is not None and parent not in cfg.directories:
        raise ConfigError(f"Unknown parent: {parent!r}")

    (cfg.vault / path).mkdir(parents=True, exist_ok=True)

    payload = _read_payload(cfg)
    payload.setdefault("directories", {})
    entry = {"path": path, "title": title, "custom": True}
    if summary:
        entry["summary"] = summary
    if when_not:
        entry["when_not"] = when_not
    if ai_notes:
        entry["ai_notes"] = ai_notes

    if parent is None:
        payload["directories"][logical_name] = entry
    else:
        parent_entry = payload["directories"].setdefault(parent, {"path": cfg.dir(parent)})
        parent_entry.setdefault("children", {})[logical_name] = entry

    _write_payload(cfg, payload)
    return {"logical_name": logical_name, "path": path, "parent": parent, "created": True}


def set_fields(cfg: Config, logical_name: str, **updates) -> dict:
    if logical_name not in cfg.directories:
        raise ConfigError(f"Unknown logical directory: {logical_name!r}")
    payload = _read_payload(cfg)
    directories = payload.setdefault("directories", {})
    existing = directories.get(logical_name)
    if isinstance(existing, str):
        existing = {"path": existing}
    elif not isinstance(existing, dict):
        existing = {"path": cfg.dir(logical_name)}
    existing.update({k: v for k, v in updates.items() if v is not None})
    directories[logical_name] = existing
    _write_payload(cfg, payload)
    return {"logical_name": logical_name, "updated": sorted(updates)}


def remove(cfg: Config, logical_name: str) -> dict:
    if logical_name not in cfg.directories:
        raise ConfigError(f"Unknown logical directory: {logical_name!r}")
    if logical_name in DIRECTORY_META:
        raise ConfigError(
            f"Refusing to remove built-in logical directory: {logical_name!r}. "
            f"Only custom entries (added via `about add`) can be removed."
        )
    payload = _read_payload(cfg)
    del payload["directories"][logical_name]
    _write_payload(cfg, payload)
    actual = cfg.dir(logical_name)
    return {
        "logical_name": logical_name,
        "removed": True,
        "note": f"Folder {actual!r} was NOT deleted from disk",
    }


def sync(cfg: Config) -> dict:
    payload = _read_payload(cfg)
    # 升级 directories：把字符串形式包成对象
    new_dirs: dict[str, dict] = {}
    for key, value in (payload.get("directories") or {}).items():
        if isinstance(value, str):
            new_dirs[key] = {"path": value}
        elif isinstance(value, dict):
            new_dirs[key] = dict(value)
    # 补齐所有默认 key
    for key, default_path in DIRECTORIES.items():
        new_dirs.setdefault(key, {"path": default_path})
    payload["directories"] = new_dirs
    _write_payload(cfg, payload)
    return {"schema_version": SCHEMA_VERSION, "directories": sorted(new_dirs)}
