from __future__ import annotations

import json
import os
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
    "90_Plans",
]


@dataclass(slots=True)
class Config:
    vault: Path
    vault_id: str
    language: str = "zh-CN"
    index_dirs: list[str] = field(default_factory=lambda: list(DEFAULT_DIRS))
    semantic_backend: str = "auto"

    @property
    def cache_dir(self) -> Path:
        if os.name == "nt":
            root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        return root / "deeporbit" / self.vault_id


def _normalized_payload(raw: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "vault_id": raw.get("vault_id") or str(uuid.uuid4()),
        "language": raw.get("language", "zh-CN"),
        "index": {
            "directories": raw.get("index", {}).get("directories", list(DEFAULT_DIRS)),
            "semantic_backend": raw.get("index", {}).get("semantic_backend", "auto"),
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
    if create and payload != raw:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return Config(
        vault=root,
        vault_id=payload["vault_id"],
        language=payload["language"],
        index_dirs=list(payload["index"]["directories"]),
        semantic_backend=payload["index"]["semantic_backend"],
    )
