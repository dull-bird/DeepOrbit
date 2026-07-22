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
DEFAULT_DIRS = [
    "00_Inbox",
    "10_Diary",
    "15_Writings",
    "20_Projects",
    "30_Research",
    "40_Wiki",
    "50_Resources",
    "60_Notes",
    "70_Family",
    "90_Plans",
]


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
    return {
        "schema_version": SCHEMA_VERSION,
        "vault_id": raw.get("vault_id") or str(uuid.uuid4()),
        "language": raw.get("language", "zh-CN"),
        "host": raw.get("host", ""),
        "index": {
            "directories": raw.get("index", {}).get("directories", list(DEFAULT_DIRS)),
            "semantic_backend": raw.get("index", {}).get("semantic_backend", "auto"),
        },
        "readonly": {
            "directories": raw.get("readonly", {}).get("directories", []),
        },
        "privacy": _normalize_privacy(raw.get("privacy", {})),
    }


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
    return {
        "outbound_mode": raw.get("outbound_mode", DEFAULT_PRIVACY["outbound_mode"]),
        "confirm_high_risk": raw.get("confirm_high_risk", DEFAULT_PRIVACY["confirm_high_risk"]),
        "rules": rules,
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
    )


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
