"""Deterministic file triage: what is valuable, where it goes, what is junk.

The CLI classifies; it never moves or deletes. The agent (do.organize) presents
the classification, the user approves, execution happens with mv / trash.
Semantic value judgment stays with the agent — every answer here carries a
reason so the agent can defend or override it.

Actions:
  keep         — already in place (skeleton dirs, runtime dotfiles, root allowlist)
  inbox        — capture: route to the configured inbox dir
  research     — research content: route to the configured research dir
  notes        — literature/knowledge notes: route to the configured notes dir
  resources    — media/attachments: route to the configured resources dir
  out-of-vault — code, secrets, agent machine state: does not belong in a
                 synced knowledge vault at all
  trash        — junk: logs, OS files, Obsidian default welcome note, empty
                 dirs, duplicate skill packs (reversible via .trash/)
  review       — deterministic rules are inconclusive; agent must read it
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import Config
from .doctor import ROOT_WHITELIST_FILES, ROOT_WHITELIST_PREFIXES
from .frontmatter import read_fields

CODE_EXT = {".py", ".sh", ".js", ".ts", ".mjs", ".rb", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".tex", ".bst", ".bbl", ".sty", ".cls"}
JUNK_EXT = {".log", ".tmp", ".bak", ".bsp", ".pyc", ".DS_Store"}
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".mp3", ".mp4", ".m4a", ".wav", ".mov", ".pdf", ".srt", ".vtt", ".tsv", ".zip", ".csv"}
SECRET_NAMES = {".env"} | {f".env.{suffix}" for suffix in ("local", "dev", "development", "prod", "production", "secret", "secrets")}
SECRET_KEY_RE = re.compile(r"(?i)(api[_-]?key|secret|token|password|private[_-]?key)\s*=")
WELCOME_MARKERS = ("这是你的新", "This is your new vault", "Welcome to Obsidian")
DATED_NOTE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(\.\w+)?$")


def _is_root_kept(name: str) -> bool:
    return name in ROOT_WHITELIST_FILES or any(name.startswith(prefix) for prefix in ROOT_WHITELIST_PREFIXES)


def _classify_md(config: Config, path: Path, head: str) -> dict:
    if any(marker in head for marker in WELCOME_MARKERS):
        return {"action": "trash", "reason": "Obsidian 默认欢迎笔记，无用户内容"}
    fields = read_fields(head)
    if fields.get("status"):
        return {"action": "inbox", "reason": "带 status 的工作项但位置在骨架外，先入 inbox 再归位"}
    if fields.get("book_id") or fields.get("source"):
        return {"action": "notes", "reason": "带文献/来源元数据的笔记"}
    return {"action": "inbox", "reason": "Markdown 笔记，默认入口是 inbox 消化"}


def _classify_dir(config: Config, path: Path) -> dict:
    entries = list(path.rglob("*"))
    files = [p for p in entries if p.is_file()]
    if not files:
        return {"action": "trash", "reason": "空目录"}
    names = {p.name for p in files}
    if "SKILL.md" in names or "ACKNOWLEDGMENTS.md" in names:
        system_skills = config.path("system") / "DeepOrbit" / "skills"
        if system_skills.is_dir():
            return {"action": "trash", "reason": "skills 重复拷贝（权威副本在 99_System/DeepOrbit/skills 与全局安装）"}
        return {"action": "review", "reason": "疑似 skill 包但 vault 内无权威副本可比对"}
    dated = sum(1 for p in files if DATED_NOTE_RE.match(p.name))
    if files and dated / len(files) > 0.7 and all(p.suffix == ".md" for p in files):
        return {"action": "out-of-vault", "reason": "日期命名的 agent 运行日志（机器状态，不进 vault）"}
    if any(p.suffix in CODE_EXT for p in files):
        return {"action": "out-of-vault", "reason": "含代码/工程文件的目录，应属代码仓库"}
    if any(p.suffix in MEDIA_EXT for p in files):
        return {"action": "resources", "reason": "以媒体/附件为主的目录"}
    return {"action": "review", "reason": "目录内容性质不明确，需要 agent 阅读判断"}


def classify(config: Config, path: Path) -> dict:
    """Classify one path. Never raises on filesystem oddities."""
    rel = str(path.relative_to(config.vault)) if path.is_relative_to(config.vault) else path.name
    base: dict = {"path": rel}
    if not path.exists() and not path.is_symlink():
        return {**base, "action": "trash", "reason": "悬空路径"}
    top = path.relative_to(config.vault).parts[0] if path.is_relative_to(config.vault) else ""
    name = path.name
    if name in SECRET_NAMES or (name.startswith(".env") and SECRET_KEY_RE.search(path.read_text(encoding="utf-8", errors="replace")[:4096])):
        return {**base, "action": "out-of-vault", "reason": "含密钥，同步 vault 会泄密，必须迁出"}
    if top != rel or path.parent == config.vault:
        if top.startswith("."):
            return {**base, "action": "keep", "reason": "点开头的运行时目录/文件，豁免"}
        if _is_root_kept(rel):
            return {**base, "action": "keep", "reason": "骨架或根目录白名单"}
        skeleton = {Path(d).parts[0] for d in config.index_dirs} | {Path(config.dir("system")).parts[0]}
        if top in skeleton and top != rel:
            return {**base, "action": "keep", "reason": "已在骨架目录内"}
    if path.is_dir():
        return {**base, **_classify_dir(config, path)}
    ext = path.suffix.lower()
    if ext in JUNK_EXT:
        return {**base, "action": "trash", "reason": f"垃圾扩展名 {ext}"}
    if ext in CODE_EXT:
        return {**base, "action": "out-of-vault", "reason": f"代码文件 {ext}，vault 不是代码仓库"}
    if ext in MEDIA_EXT:
        return {**base, "action": "resources", "reason": f"媒体/附件 {ext}"}
    if ext == ".md":
        head = path.read_text(encoding="utf-8", errors="replace")[:4096]
        return {**base, **_classify_md(config, path, head)}
    return {**base, "action": "review", "reason": f"未知类型 {ext or '(无扩展名)'}，需要 agent 判断"}


def triage(config: Config, paths: list[str] | None = None) -> list[dict]:
    """Classify explicit paths, or all non-allowlisted root entries by default."""
    if paths:
        targets = [(config.vault / p).resolve() if not Path(p).is_absolute() else Path(p) for p in paths]
    else:
        skeleton = {Path(d).parts[0] for d in config.index_dirs} | {Path(config.dir("system")).parts[0]}
        targets = [
            entry
            for entry in sorted(config.vault.iterdir())
            if not _is_root_kept(entry.name) and entry.name not in skeleton and not entry.name.startswith(".")
        ]
    return [classify(config, path) for path in targets]
