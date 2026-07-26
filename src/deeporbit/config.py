from __future__ import annotations

import json
import os
import socket
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError

CONFIG_NAME = "deeporbit.json"
SCHEMA_VERSION = 3

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
# Semantic metadata for each logical directory. Paths stay in DIRECTORIES;
# this table is the default source for deeporbit.json#directory_meta and the
# `deeporbit about` command. children describes sub-skeleton nodes (e.g.
# 99_System/Templates) keyed by their own logical name; children paths are
# vault-relative (not parent-relative).
DIRECTORY_META: dict[str, dict] = {
    "inbox": {
        "title": "快速捕获",
        "summary": "未经分类的想法、临时任务、待整理的剪藏；默认 Todos.md 也在这里",
        "when_not": "已经明确归属的内容直接放到对应目录，不要先进 Inbox 再搬一次",
        "ai_notes": "添加任务用 deeporbit todo add，不手改 Todos.md；整理用 deeporbit triage，不手移文件",
    },
    "diary": {
        "title": "日志",
        "summary": "Daily Notes 与短期上下文，按日期一篇一个文件",
        "when_not": "持续性主题（项目、研究、概念）不放日记，放各自目录",
        "ai_notes": "通过 deeporbit calendar / deeporbit agenda 查询；写新日记用对应技能而不是手建文件",
    },
    "writings": {
        "title": "写作",
        "summary": "用户亲笔写的内容：随笔、文章、书稿",
        "when_not": "AI 生成的草稿放 60_Notes，确认采用后才挪到这里",
        "ai_notes": "写入前必须先读现有同主题文章，避免覆盖用户文字",
    },
    "projects": {
        "title": "项目",
        "summary": "有明确目标与结束条件的工作；status 字段驱动生命周期",
        "when_not": "长期兴趣、没有结束条件的主题放 30_Research",
        "ai_notes": "状态迁移走 deeporbit pause/resume/done/archive；不要手改 frontmatter status",
        "children": {
            "paused": {"path": "20_Projects/Paused", "title": "已暂停项目"},
            "archived": {"path": "20_Projects/Archived", "title": "已归档项目"},
        },
    },
    "research": {
        "title": "研究",
        "summary": "开放性的探索与调研，可能没有结论",
        "when_not": "有交付物的具体工作放 20_Projects",
        "ai_notes": "同 projects，状态迁移走 CLI",
        "children": {
            "paused": {"path": "30_Research/Paused", "title": "已暂停研究"},
            "archived": {"path": "30_Research/Archived", "title": "已归档研究"},
        },
    },
    "wiki": {
        "title": "Wiki",
        "summary": "原子、可复用的概念笔记；Zettelkasten 风格",
        "when_not": "一次性总结、原始剪藏放 60_Notes",
        "ai_notes": "新增条目用 wikilink 串联，不复制粘贴现有内容",
    },
    "resources": {
        "title": "资源",
        "summary": "策展的外部资料：工具、书籍、链接",
        "when_not": "自己的笔记不放这里",
        "ai_notes": "附来源 URL 与获取日期",
    },
    "notes": {
        "title": "笔记",
        "summary": "摘要、原始知识捕获、AI 生成草稿",
        "when_not": "定稿的亲笔写作放 15_Writings；概念性内容进 40_Wiki",
        "ai_notes": "外部同步目录（如微信读书）由 deeporbit 标记为 readonly，不要写入",
    },
    "family": {
        "title": "家庭",
        "summary": "家庭与个人生活记录",
        "when_not": "工作相关的内容放对应工作目录",
        "ai_notes": "默认隐私等级最高；privacy 扫描默认覆盖",
    },
    "plans": {
        "title": "计划",
        "summary": "可评审的执行计划与检查点",
        "when_not": "长期目标放 projects；一次性 todo 放 inbox",
        "ai_notes": "计划文件用 deeporbit 模板生成，不手写",
    },
    "system": {
        "title": "系统",
        "summary": "DeepOrbit 自身的模板、Bases、提示词、规则、归档",
        "when_not": "用户内容永远不要放 99_System",
        "ai_notes": "本目录大部分内容由 deeporbit sync-prompts / init 物化；手写内容放 managed block 之外",
        "children": {
            "templates": {"path": "99_System/Templates", "title": "模板", "summary": "Obsidian Templater 模板"},
            "prompts": {"path": "99_System/Prompts", "title": "提示词", "summary": "运行时给 AI 的提示"},
            "bases": {"path": "99_System/Bases", "title": "Bases", "summary": "Obsidian Bases 视图定义"},
            "rules": {"path": "99_System/Rules", "title": "规则", "summary": "deeporbit heartbeat 等定时任务的规则"},
            "recipes": {"path": "99_System/Recipes", "title": "配方", "summary": "可组合的工作流配方"},
            "deeporbit-internal": {"path": "99_System/DeepOrbit", "title": "DeepOrbit 内部", "summary": "skills 图、内部数据"},
        },
    },
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
    directory_meta: dict = field(default_factory=dict)
    directories_full: dict = field(default_factory=dict)  # v3 raw form, for round-trip writing
    deeporbit_version: str = ""

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


def _merge_meta(default: dict, override: dict) -> dict:
    merged = {**default, **{k: v for k, v in override.items() if v is not None}}
    if "children" in default or "children" in override:
        default_children = default.get("children") or {}
        override_children = override.get("children") or {}
        merged["children"] = {
            key: _merge_meta(default_children.get(key, {}), override_children.get(key, {}))
            for key in {*default_children, *override_children}
        }
    return merged


def _normalize_directory_meta(raw_meta: dict, raw_directories: dict) -> dict:
    """Merge defaults with user overrides; v2 string directories contribute only paths."""
    overrides: dict[str, dict] = {}
    for key, value in (raw_meta or {}).items():
        if isinstance(value, dict):
            overrides[key] = value
    for key, value in (raw_directories or {}).items():
        if isinstance(value, dict):
            # v3 inline form: directories.inbox = {"path": ..., "title": ...}
            body = {k: v for k, v in value.items() if k != "path"}
            overrides[key] = _merge_meta(overrides.get(key, {}), body) if key in overrides else body
    return {
        key: _merge_meta(DIRECTORY_META.get(key, {}), overrides.get(key, {}))
        for key in {*DIRECTORY_META, *overrides}
    }


def _normalize_directories(raw_directories: dict) -> dict:
    """Accept v2 {key: path-str} and v3 {key: {path, ...}}; emit v3 {key: {path, ...}}.

    Unknown keys are preserved (custom directories).
    """
    out: dict[str, dict] = {}
    merged = {**{k: {"path": v} for k, v in DIRECTORIES.items()}, **(raw_directories or {})}
    for key, value in merged.items():
        if isinstance(value, str) and value.strip():
            out[key] = {"path": value.strip()}
        elif isinstance(value, dict):
            body = dict(value)
            path = str(body.pop("path", "") or "").strip()
            if not path and key in DIRECTORIES:
                path = DIRECTORIES[key]
            if not path:
                continue
            out[key] = {"path": path, **body}
    return out


def _normalized_payload(raw: dict) -> dict:
    directories = _normalize_directories(raw.get("directories", {}))
    top_level = [directories[key]["path"] for key in ("inbox", "diary", "writings", "projects", "research", "wiki", "resources", "notes", "family", "plans")]
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
        "directory_meta": _normalize_directory_meta(raw.get("directory_meta"), raw.get("directories")),
        "deeporbit_version": raw.get("deeporbit_version", ""),
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
        directories={key: value["path"] for key, value in payload["directories"].items()},
        directories_full=dict(payload["directories"]),
        directory_meta=dict(payload["directory_meta"]),
        deeporbit_version=payload["deeporbit_version"],
    )


def stamp_version(vault: Path | str) -> str:
    """Record the running DeepOrbit version into deeporbit.json."""
    from . import __version__

    root = Path(vault).expanduser().resolve()
    path = root / CONFIG_NAME
    raw: dict = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
    payload = _normalized_payload(raw)
    payload["deeporbit_version"] = __version__
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return __version__


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
