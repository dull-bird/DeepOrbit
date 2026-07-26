from __future__ import annotations

import json
from pathlib import Path

import pytest

from deeporbit.config import (
    CONFIG_NAME,
    DIRECTORY_META,
    DIRECTORIES,
    SCHEMA_VERSION,
    load_config,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / CONFIG_NAME).write_text(
        json.dumps({"schema_version": 2, "directories": {"inbox": "00_Inbox"}}),
        encoding="utf-8",
    )
    for d in DIRECTORIES.values():
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_directory_meta_covers_all_logical_names():
    for key in DIRECTORIES:
        assert key in DIRECTORY_META, f"missing meta for {key}"
        meta = DIRECTORY_META[key]
        assert meta.get("title"), f"{key}.title empty"
        assert meta.get("summary"), f"{key}.summary empty"


def test_directory_meta_system_has_children():
    system = DIRECTORY_META["system"]
    children = system.get("children") or {}
    for sub in ("templates", "prompts", "bases", "rules", "recipes", "deeporbit-internal"):
        assert sub in children, f"missing system.children.{sub}"


def test_load_config_exposes_directory_meta(vault):
    cfg = load_config(vault)
    assert "inbox" in cfg.directory_meta
    assert cfg.directory_meta["inbox"]["title"]
    # 默认表 merge：用户 json 没写的字段从默认表补
    assert cfg.directory_meta["inbox"]["summary"]


def test_children_keys_unprefixed():
    projects_children = DIRECTORY_META["projects"]["children"]
    assert "paused" in projects_children
    assert "archived" in projects_children
    research_children = DIRECTORY_META["research"]["children"]
    assert "paused" in research_children
    assert "archived" in research_children
