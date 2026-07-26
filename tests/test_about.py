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


from deeporbit import about as about_mod


def test_about_tree_returns_all_top_level(vault):
    cfg = load_config(vault)
    tree = about_mod.tree(cfg)
    names = {node["logical_name"] for node in tree}
    for expected in ("inbox", "diary", "projects", "system"):
        assert expected in names
    inbox = next(n for n in tree if n["logical_name"] == "inbox")
    assert inbox["path"] == "00_Inbox"
    assert inbox["title"] == DIRECTORY_META["inbox"]["title"]


def test_about_lookup_by_logical_name(vault):
    cfg = load_config(vault)
    node = about_mod.lookup(cfg, "inbox")
    assert node["logical_name"] == "inbox"
    assert node["path"] == "00_Inbox"


def test_about_lookup_by_path(vault):
    cfg = load_config(vault)
    node = about_mod.lookup(cfg, "00_Inbox")
    assert node["logical_name"] == "inbox"


def test_about_lookup_by_title(vault):
    cfg = load_config(vault)
    node = about_mod.lookup(cfg, DIRECTORY_META["inbox"]["title"])
    assert node["logical_name"] == "inbox"


def test_about_lookup_unknown_raises(vault):
    cfg = load_config(vault)
    with pytest.raises(KeyError):
        about_mod.lookup(cfg, "no-such-thing")


def test_about_flatten_includes_children(vault):
    cfg = load_config(vault)
    flat = about_mod.flatten(cfg)
    # 注意：children 键名是 unprefixed（templates/paused/...），同名 child 可能出现在多个 parent 下，
    # 因此用 (parent, logical_name) 联合断言
    pairs = {(n.get("parent"), n["logical_name"]) for n in flat}
    assert ("system", "templates") in pairs
    assert ("projects", "paused") in pairs
    assert ("projects", "archived") in pairs
    assert ("research", "paused") in pairs


from deeporbit.errors import ConfigError


def test_about_add_creates_directory_and_entry(vault):
    cfg = load_config(vault)
    result = about_mod.add(
        cfg,
        logical_name="books",
        path="80_Books",
        title="读书笔记",
        summary="用户自定义",
    )
    assert (vault / "80_Books").is_dir()
    assert result["logical_name"] == "books"
    cfg2 = load_config(vault)
    assert cfg2.dir("books") == "80_Books"
    assert cfg2.directory_meta["books"]["title"] == "读书笔记"
    assert cfg2.directory_meta["books"]["custom"] is True


def test_about_add_conflict_raises(vault):
    cfg = load_config(vault)
    with pytest.raises(ConfigError):
        about_mod.add(cfg, logical_name="inbox", path="X", title="dup")


def test_about_add_with_parent_nests_under_children(vault):
    cfg = load_config(vault)
    about_mod.add(
        cfg,
        logical_name="projects-active",
        path="20_Projects/Active",
        title="进行中的项目",
        parent="projects",
    )
    cfg2 = load_config(vault)
    children = cfg2.directory_meta["projects"]["children"]
    assert "projects-active" in children
    assert children["projects-active"]["path"] == "20_Projects/Active"


def test_about_set_partial_update(vault):
    cfg = load_config(vault)
    about_mod.set_fields(cfg, "inbox", title="新标题")
    cfg2 = load_config(vault)
    assert cfg2.directory_meta["inbox"]["title"] == "新标题"
    # 其他字段保留默认
    assert cfg2.directory_meta["inbox"]["summary"] == DIRECTORY_META["inbox"]["summary"]


def test_about_remove_custom_only(vault):
    cfg = load_config(vault)
    about_mod.add(cfg, logical_name="books", path="80_Books", title="读书笔记")
    cfg = load_config(vault)
    about_mod.remove(cfg, "books")
    cfg2 = load_config(vault)
    assert "books" not in cfg2.directories
    # 实际目录保留
    assert (vault / "80_Books").is_dir()


def test_about_remove_builtin_rejected(vault):
    cfg = load_config(vault)
    with pytest.raises(ConfigError):
        about_mod.remove(cfg, "inbox")


def test_about_sync_rewrites_v3(vault):
    # 先手动写一个 v2 json 模拟旧 vault
    (vault / CONFIG_NAME).write_text(
        json.dumps({"schema_version": 2, "directories": {"inbox": "00_Inbox"}}),
        encoding="utf-8",
    )
    cfg = load_config(vault)
    result = about_mod.sync(cfg)
    raw = json.loads((vault / CONFIG_NAME).read_text(encoding="utf-8"))
    assert raw["schema_version"] == 3
    assert raw["directories"]["inbox"]["path"] == "00_Inbox"
    assert result["schema_version"] == 3


def test_doctor_flags_v2_schema(tmp_path):
    (tmp_path / CONFIG_NAME).write_text(
        json.dumps({"schema_version": 2, "directories": {"inbox": "00_Inbox"}}),
        encoding="utf-8",
    )
    for d in DIRECTORIES.values():
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    from deeporbit.doctor import diagnose
    cfg = load_config(tmp_path)
    report = diagnose(cfg)
    issues = json.dumps(report, ensure_ascii=False)
    assert "schema_version" in issues or "v3" in issues or "about sync" in issues
