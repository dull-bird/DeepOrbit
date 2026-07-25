from __future__ import annotations

import json
import os
import socket
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError

CONFIG_NAME = "deeporbit.json"
SCHEMA_VERSION = 2

# Logical directory map: the single source of truth for vault layout.
# deeporbit.json may override any entry under "directories"; every module
# resolves paths through Config.dir() — never through string literals.
DIRECTORIES = {
    "inbox": "00_Inbox",
    "diary": "10_Diary",
    "writings": "15_Writings",
    "projects": "20_Projects",
    "research": "30_Research",
    "wiki": "40_Wiki",
    "resources": "50_Resources",
    "notes": "60_Notes",
    "family": "70_Family",
    "plans": "90_Plans",
    "system": "99_System",
}
DEFAULT_DIRS = [DIRECTORIES[key] for key in ("inbox", "diary", "writings", "projects", "research", "wiki", "resources", "notes", "family", "plans")]

# Second-level skeleton: status-based subfolders inside projects/research.
# active items stay at the section root; paused/archived are filed away.
STATUS_SECTIONS = ("projects", "research")
STATUS_SUBDIRS = ("Paused", "Archived")


def skeleton_dirs(directories: dict | None = None) -> list[str]:
    """Full skeleton: configured top-level dirs + status subfolders."""
    mapping = {**DIRECTORIES, **(directories or {})}
    dirs = [mapping[key] for key in ("inbox", "diary", "writings", "projects", "research", "wiki", "resources", "notes", "family", "plans", "system")]
    for section in STATUS_SECTIONS:
        for sub in STATUS_SUBDIRS:
            dirs.append(f"{mapping[section]}/{sub}")
    return dirs


@dataclass(slots=True)
class Config:
    vault: Path
    vault_id: str
    language: str = "zh-CN"
    index_dirs: list[str] = field(default_factory=lambda: list(DEFAULT_DIRS))
    semantic_backend: str = "auto"
    readonly_dirs: list[str] = field(default_factory=list)
    host: str = ""
    privacy: dict = field(default_factory=dict)
    agent: dict = field(default_factory=dict)
    directories: dict = field(default_factory=lambda: dict(DIRECTORIES))

    def dir(self, name: str) -> str:
        """Vault-relative path for a logical directory ('inbox', 'projects', …)."""
        if name not in self.directories:
            raise ConfigError(f"Unknown logical directory: {name!r} (known: {sorted(self.directories)})")
        return self.directories[name]

    def path(self, name: str) -> Path:
        """Absolute path for a logical directory."""
        return self.vault / self.dir(name)

    @property
    def cache_dir(self) -> Path:
        if os.name == "nt":
            root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        return root / "deeporbit" / self.vault_id


DEFAULT_PRIVACY = {
    "outbound_mode": "redact",
    "confirm_high_risk": True,
    "rules": [
        {"name": "email", "enabled": True, "severity": "high"},
        {"name": "phone", "enabled": True, "severity": "high"},
        {"name": "secret", "enabled": True, "severity": "high"},
        {"name": "card", "enabled": True, "severity": "high"},
        {"name": "id_number", "enabled": True, "severity": "high"},
    ],
}


def _normalized_payload(raw: dict) -> dict:
    directories = {
        **DIRECTORIES,
        **{k: str(v).strip() for k, v in raw.get("directories", {}).items() if k in DIRECTORIES and isinstance(v, str) and v.strip()},
    }
    top_level = [directories[key] for key in ("inbox", "diary", "writings", "projects", "research", "wiki", "resources", "notes", "family", "plans")]
    return {
        "schema_version": SCHEMA_VERSION,
        "vault_id": raw.get("vault_id") or str(uuid.uuid4()),
        "language": raw.get("language", "zh-CN"),
        "host": raw.get("host", ""),
        "index": {
            "directories": raw.get("index", {}).get("directories") or top_level,
            "semantic_backend": raw.get("index", {}).get("semantic_backend", "auto"),
        },
        "readonly": {
            "directories": raw.get("readonly", {}).get("directories", []),
        },
        "directories": directories,
        "privacy": _normalize_privacy(raw.get("privacy", {})),
        "agent": _normalize_agent(raw.get("agent", {})),
    }


def _normalize_agent(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return {}
    entry = {}
    if raw.get("name"):
        entry["name"] = str(raw["name"])
    if raw.get("mode"):
        entry["mode"] = str(raw["mode"])
    if raw.get("updated"):
        entry["updated"] = str(raw["updated"])
    return entry


def _normalize_privacy(raw: dict) -> dict:
    user_rules = raw.get("rules", [])
    seen = {rule.get("name") for rule in user_rules if rule.get("name")}
    rules = []
    for rule in user_rules:
        name = rule.get("name")
        if not name:
            continue
        default = next((r for r in DEFAULT_PRIVACY["rules"] if r["name"] == name), None)
        if default:
            rules.append({**default, **rule})
        else:
            rules.append({"name": name, "enabled": bool(rule.get("enabled", True)), "severity": rule.get("severity", "medium")})
    for default in DEFAULT_PRIVACY["rules"]:
        if default["name"] not in seen:
            rules.append(dict(default))
    if not rules:
        rules = [dict(r) for r in DEFAULT_PRIVACY["rules"]]
    scan = raw.get("scan", {})
    return {
        "outbound_mode": raw.get("outbound_mode", DEFAULT_PRIVACY["outbound_mode"]),
        "confirm_high_risk": raw.get("confirm_high_risk", DEFAULT_PRIVACY["confirm_high_risk"]),
        "rules": rules,
        "scan": {
            "exclude": list(scan.get("exclude", ["60_Notes/微信读书", "node_modules"])),
            "thresholds": scan.get("thresholds", {}),
            "category_cap": int(scan.get("category_cap", 6)),
            "llm_verify": bool(scan.get("llm_verify", False)),
        },
    }


def load_config(vault: Path | str, *, create: bool = False) -> Config:
    root = Path(vault).expanduser().resolve()
    if not root.is_dir():
        raise ConfigError(f"Vault does not exist: {root}")
    path = root / CONFIG_NAME
    raw: dict = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Invalid {CONFIG_NAME}: {exc}") from exc
    payload = _normalized_payload(raw)
    if create and not payload["host"]:
        payload["host"] = socket.gethostname()
    if create and payload != raw:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return Config(
        vault=root,
        vault_id=payload["vault_id"],
        language=payload["language"],
        index_dirs=list(payload["index"]["directories"]),
        semantic_backend=payload["index"]["semantic_backend"],
        readonly_dirs=list(payload["readonly"]["directories"]),
        host=payload["host"],
        privacy=payload["privacy"],
        agent=dict(payload["agent"]),
        directories=dict(payload["directories"]),
    )


def save_agent(vault: Path | str, agent: dict | None) -> None:
    """Persist (or clear, when None) the agent CLI choice in deeporbit.json."""
    root = Path(vault).expanduser().resolve()
    path = root / CONFIG_NAME
    raw: dict = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Invalid {CONFIG_NAME}: {exc}") from exc
    payload = _normalized_payload(raw)
    payload["agent"] = dict(agent) if agent else {}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_readonly_dirs(vault: Path | str, directories: list[str]) -> None:
    """Persist readonly directories into deeporbit.json, preserving other sections."""
    root = Path(vault).expanduser().resolve()
    path = root / CONFIG_NAME
    raw: dict = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Invalid {CONFIG_NAME}: {exc}") from exc
    payload = _normalized_payload(raw)
    payload["readonly"]["directories"] = sorted(dict.fromkeys(directories))
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
