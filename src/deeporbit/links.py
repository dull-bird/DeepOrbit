from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import CONFIG_NAME
from .errors import DeepOrbitError

REGISTRY_NAME = "links.json"


class LinkError(DeepOrbitError):
    code = "LINK_ERROR"

@dataclass(slots=True)
class Link:
    name: str
    path: Path
    linked_at: str
    last_used_at: str = ""
    deeporbit: bool = False
    obsidian_opened: bool = False
    description: str = ""
    description_source: str = ""  # "user" | "agent"; empty when no description yet
    description_updated_at: str = ""
    is_default: bool = False


def registry_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "deeporbit" / REGISTRY_NAME


def _load() -> dict:
    path = registry_path()
    if not path.exists():
        return {"default": None, "links": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LinkError(f"Invalid link registry {path}: {exc}") from exc
    raw.setdefault("default", None)
    raw.setdefault("links", {})
    return raw


def _save(data: dict) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _markers(path: Path) -> tuple[bool, bool]:
    deeporbit = (path / CONFIG_NAME).is_file()
    obsidian_opened = (path / ".obsidian" / "app.json").is_file()
    return deeporbit, obsidian_opened

def _to_link(name: str, entry: dict, default: str | None) -> Link:
    path = Path(entry["path"])
    deeporbit, obsidian_opened = _markers(path) if path.is_dir() else (False, False)
    return Link(
        name=name,
        path=path,
        linked_at=entry.get("linked_at", ""),
        last_used_at=entry.get("last_used_at", ""),
        deeporbit=deeporbit,
        obsidian_opened=obsidian_opened,
        description=entry.get("description", ""),
        description_source=entry.get("description_source", ""),
        description_updated_at=entry.get("description_updated_at", ""),
        is_default=name == default,
    )


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token}


def _score_link(link: Link, query: str) -> tuple[int, str]:
    normalized = query.strip().lower()
    if not normalized:
        return (0, "")

    score = 0
    reasons: list[str] = []
    name = link.name.lower()
    description = link.description.lower().strip()
    query_tokens = _tokenize(normalized)
    name_tokens = _tokenize(name)
    description_tokens = _tokenize(description)

    if normalized == name or normalized == f"@{name}":
        return (1000, "exact name match")
    if name and name in normalized:
        score += 300
        reasons.append("name substring")
    if description:
        if normalized == description:
            score += 250
            reasons.append("exact description match")
        elif normalized in description or description in normalized:
            score += 180
            reasons.append("description substring")
    if name_tokens:
        name_overlap = len(query_tokens & name_tokens)
        if name_overlap:
            score += name_overlap * 80
            reasons.append(f"{name_overlap} name token(s)")
    if description_tokens:
        description_overlap = len(query_tokens & description_tokens)
        if description_overlap:
            score += description_overlap * 20
            reasons.append(f"{description_overlap} description token(s)")
    if link.is_default:
        score += 5
        reasons.append("default")
    return score, ", ".join(reasons)


def _links(data: dict) -> list[Link]:
    default = data["default"]
    return [_to_link(name, entry, default) for name, entry in sorted(data["links"].items())]


def _touch_link(name: str) -> Link:
    data = _load()
    entry = data["links"].get(name)
    if entry is None:
        raise LinkError(f"Unknown link: {name}")
    entry["last_used_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _save(data)
    return _to_link(name, entry, data["default"])


def select_link(query: str) -> tuple[Link, str]:
    data = _load()
    links = _links(data)
    if not links:
        raise LinkError("No links registered")

    normalized = query.strip()
    if not normalized:
        default_name = data["default"]
        if not default_name:
            raise LinkError("No default link configured")
        selected = _to_link(default_name, data["links"][default_name], default_name)
        return selected, "default"

    best_score = -1
    best: list[tuple[Link, str]] = []
    for link in links:
        score, reason = _score_link(link, normalized)
        if score > best_score:
            best_score = score
            best = [(link, reason)]
        elif score == best_score and score > 0:
            best.append((link, reason))

    if best_score <= 0:
        default_name = data["default"]
        if not default_name:
            raise LinkError("No default link configured")
        selected = _to_link(default_name, data["links"][default_name], default_name)
        return selected, "default"
    if len(best) > 1:
        names = ", ".join(link.name for link, _ in best)
        raise LinkError(f"Ambiguous vault routing for {query!r}: {names}")
    return best[0]


def route_link(query: str) -> dict:
    link, reason = select_link(query)
    touched = _touch_link(link.name)
    return {
        "query": query,
        "reason": reason,
        "selected": {
            "name": touched.name,
            "path": str(touched.path),
            "linked_at": touched.linked_at,
            "last_used_at": touched.last_used_at,
            "deeporbit": touched.deeporbit,
            "obsidian_opened": touched.obsidian_opened,
            "description": touched.description,
            "description_source": touched.description_source,
            "description_updated_at": touched.description_updated_at,
            "is_default": touched.is_default,
        },
    }


def add_link(name: str, vault: Path | str, *, description: str = "", source: str = "") -> Link:
    if not name or name.startswith("@") or "/" in name or "\\" in name:
        raise LinkError(f"Invalid link name: {name!r}")
    path = Path(vault).expanduser().resolve()
    if not path.is_dir():
        raise LinkError(f"Vault does not exist: {path}")
    entry = {
        "path": str(path),
        "linked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if description:
        entry["description"] = description
        entry["description_source"] = source or "user"
        entry["description_updated_at"] = entry["linked_at"]
    data = _load()
    data["links"][name] = entry
    if not data["default"]:
        data["default"] = name
    _save(data)
    return _to_link(name, data["links"][name], data["default"])


def describe_link(name: str, description: str, *, source: str = "user") -> Link:
    """Set or refine a vault's purpose description.

    `source` records who wrote the description ("user" or "agent") so agents can
    refine their own summaries over time while leaving user-authored text alone
    unless the user confirms.
    """
    data = _load()
    entry = data["links"].get(name)
    if entry is None:
        raise LinkError(f"Unknown link: {name}")
    entry["description"] = description
    entry["description_source"] = source
    entry["description_updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _save(data)
    return _to_link(name, entry, data["default"])


def list_links() -> list[Link]:
    data = _load()
    return _links(data)


def remove_link(name: str) -> Link:
    data = _load()
    entry = data["links"].pop(name, None)
    if entry is None:
        raise LinkError(f"Unknown link: {name}")
    if data["default"] == name:
        data["default"] = next(iter(sorted(data["links"])), None)
    _save(data)
    return _to_link(name, entry, data["default"])


def set_default(name: str) -> Link:
    data = _load()
    entry = data["links"].get(name)
    if entry is None:
        raise LinkError(f"Unknown link: {name}")
    data["default"] = name
    _save(data)
    return _to_link(name, entry, name)


def resolve_vault(vault: str) -> Path:
    """Resolve a `--vault` argument; `@name` looks up the link registry."""
    if not vault.startswith("@"):
        return Path(vault)
    name = vault[1:]
    data = _load()
    if name == "":
        name = data["default"] or ""
    entry = data["links"].get(name)
    if entry is None:
        known = ", ".join(sorted(data["links"])) or "none"
        raise LinkError(f"Unknown link: @{name or '?'} (registered: {known})")
    return _touch_link(name).path
