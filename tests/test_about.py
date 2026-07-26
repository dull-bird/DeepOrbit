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


def test_v2_string_directories_are_upgraded_on_write(vault):
    # v2 写入的字符串形式，读取后 _normalized_payload 应升级为对象形式
    cfg = load_config(vault, create=True)
    raw = json.loads((vault / CONFIG_NAME).read_text(encoding="utf-8"))
    assert raw["schema_version"] == 3
    assert isinstance(raw["directories"]["inbox"], dict)
    assert raw["directories"]["inbox"]["path"] == "00_Inbox"


def test_v3_inline_overrides_merge_with_defaults(tmp_path):
    (tmp_path / CONFIG_NAME).write_text(
        json.dumps({
            "schema_version": 3,
            "directories": {
                "inbox": {"path": "00_收件箱", "title": "自定义收件箱"},
            },
        }),
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    # 路径来自用户
    assert cfg.dir("inbox") == "00_收件箱"
    # title 来自用户
    assert cfg.directory_meta["inbox"]["title"] == "自定义收件箱"
    # summary 缺省，从默认表补
    assert cfg.directory_meta["inbox"]["summary"] == DIRECTORY_META["inbox"]["summary"]


def test_user_custom_directory_accepted(tmp_path):
    (tmp_path / CONFIG_NAME).write_text(
        json.dumps({
            "schema_version": 3,
            "directories": {
                "books": {
                    "path": "80_Books",
                    "title": "读书笔记",
                    "summary": "用户自定义",
                    "custom": True,
                },
            },
        }),
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.dir("books") == "80_Books"
    assert cfg.directory_meta["books"]["custom"] is True
