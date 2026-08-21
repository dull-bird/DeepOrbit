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

Second stage (`triage --inbox`, see route_inbox): items already sitting in the
configured inbox dir are routed to a concrete destination (diary / projects /
research / notes / resources / keep for managed files), or trash for empty
notes and exact duplicates, or review when only the agent can judge.
"""

from __future__ import annotations

import hashlib
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


def triage(config: Config, paths: list[str] | None = None, inbox: bool = False) -> list[dict]:
    """Classify explicit paths, or all non-allowlisted root entries by default.

    With inbox=True, route the configured inbox dir instead (second stage:
    captured items get a concrete destination, trash, or review)."""
    if inbox:
        return route_inbox(config)
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


# ---------------------------------------------------------------------------
# Inbox routing (second stage)
#
# Items already captured in the inbox get a concrete destination instead of
# the generic "inbox" action. Same contract as classify(): deterministic,
# JSON only, never moves anything; semantic judgment still escalates to
# "review" for the agent.
# ---------------------------------------------------------------------------

INBOX_TINY_CHARS = 30
INBOX_MANAGED_NAMES = {"Todos.md"}
EXTERNAL_TYPES = {"note", "paper", "transcript", "podcast", "video", "reference", "clipping", "article"}
DIARY_TYPES = {"diary", "daily", "journal"}
_BASE64_RUN_RE = re.compile(r"[A-Za-z0-9+/=]{200,}")
_URL_RE = re.compile(r"https?://", re.I)
_MEETING_NAME_RE = re.compile(r"(?i)会议|纪要|例会|周会|standup|meeting")
_DATED_NAME_RE = re.compile(r"\d{4}[-/年.]\d{1,2}[-/月.]\d{1,2}")
_LINK_NAME_RE = re.compile(r"(?i)链接汇总|书签|收藏夹|links?\b|bookmarks?")


def _is_link_collection(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    url_lines = sum(1 for line in lines if _URL_RE.search(line))
    return url_lines >= 3 and url_lines / len(lines) >= 0.5


def _is_data_dump(text: str) -> bool:
    """Inline base64 payloads (accidental image pastes) dominate the note.

    Whitespace is stripped first because pasted data URIs are often
    line-wrapped (e.g. at 76 columns), which would split the runs."""
    if "base64," not in text:
        return False
    compact = re.sub(r"\s+", "", text)
    blob = sum(len(m.group()) for m in _BASE64_RUN_RE.finditer(compact))
    return blob > 0 and blob / max(len(compact), 1) > 0.5


def _normalized_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _duplicate_map(files: list[Path]) -> dict[Path, Path]:
    """Map each duplicate .md file to the survivor it duplicates.

    Survivor is the oldest (mtime, then name) file in each content-identical
    group, so the result is stable across runs."""
    groups: dict[str, list[Path]] = {}
    for path in files:
        try:
            groups.setdefault(_normalized_hash(path.read_text(encoding="utf-8", errors="replace")), []).append(path)
        except OSError:
            continue
    duplicates: dict[Path, Path] = {}
    for group in groups.values():
        if len(group) < 2:
            continue
        group.sort(key=lambda p: (p.stat().st_mtime, p.name))
        for dup in group[1:]:
            duplicates[dup] = group[0]
    return duplicates


def route_inbox_item(config: Config, path: Path, dup_of: Path | None = None) -> dict:
    """Route one inbox item to its destination. Never raises, never moves."""
    rel = str(path.relative_to(config.vault)) if path.is_relative_to(config.vault) else path.name
    base: dict = {"path": rel}

    def routed(action: str, reason: str) -> dict:
        result = {**base, "action": action, "reason": reason}
        if action in config.directories:
            result["target"] = config.dir(action)
        return result

    name = path.name
    if name in INBOX_MANAGED_NAMES:
        return routed("keep", "DeepOrbit 管理的任务文件，留在 inbox")
    if name in SECRET_NAMES or (name.startswith(".env") and SECRET_KEY_RE.search(path.read_text(encoding="utf-8", errors="replace")[:4096])):
        return routed("out-of-vault", "含密钥，同步 vault 会泄密，必须迁出")
    if path.is_dir():
        result = {**base, **_classify_dir(config, path)}
        if result["action"] in config.directories:
            result["target"] = config.dir(result["action"])
        return result
    ext = path.suffix.lower()
    if ext in JUNK_EXT:
        return routed("trash", f"垃圾扩展名 {ext}")
    if ext in CODE_EXT:
        return routed("out-of-vault", f"代码文件 {ext}，vault 不是代码仓库")
    if ext in MEDIA_EXT:
        return routed("resources", f"媒体/附件 {ext}")
    if ext != ".md":
        return routed("review", f"未知类型 {ext or '(无扩展名)'}，需要 agent 判断")

    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return routed("trash", "空笔记")
    if dup_of is not None:
        dup_rel = str(dup_of.relative_to(config.vault)) if dup_of.is_relative_to(config.vault) else dup_of.name
        return routed("trash", f"与 {dup_rel} 内容完全重复")

    fields = read_fields(text[:4096])
    ftype = fields.get("type", "").lower()
    if fields.get("status"):
        dest = "research" if ftype == "research" else "projects"
        return routed(dest, f"带 status 的工作项，归属 {config.dir(dest)}")
    if ftype in DIARY_TYPES:
        return routed("diary", f"frontmatter type={ftype}，按日期归档")
    if fields.get("book_id") or fields.get("source") or ftype in EXTERNAL_TYPES:
        return routed("notes", "带文献/来源元数据的笔记")
    stem = path.stem
    if _DATED_NAME_RE.search(stem) and _MEETING_NAME_RE.search(stem):
        return routed("diary", "日期+会议类命名，属于日志")
    if _is_link_collection(text):
        return routed("resources", "以链接清单为主，属于策展的外部资料")
    if _LINK_NAME_RE.search(stem) and len(_URL_RE.findall(text)) >= 3:
        return routed("resources", "命名为链接汇总且含多条 URL，属于策展的外部资料")
    if _is_data_dump(text):
        return routed("review", "几乎全是 base64 内联数据，疑似误粘贴，需 agent 确认")
    if len(re.sub(r"\s+", "", text)) < INBOX_TINY_CHARS:
        return routed("review", "内容过短，需 agent 判断是任务、想法还是垃圾")
    return routed("review", "确定性规则无法判断语义归属，需 agent 阅读")


def route_inbox(config: Config) -> list[dict]:
    """Route every top-level entry of the configured inbox dir."""
    inbox = config.path("inbox")
    if not inbox.is_dir():
        return []
    entries = [entry for entry in sorted(inbox.iterdir()) if not entry.name.startswith(".")]
    md_files = [entry for entry in entries if entry.is_file() and entry.suffix.lower() == ".md"]
    duplicates = _duplicate_map(md_files)
    return [route_inbox_item(config, entry, duplicates.get(entry)) for entry in entries]


# ---------------------------------------------------------------------------
# Auto-execution (--apply)
#
# Only high-confidence actions are executed: trash is reversible (.trash/),
# destination routes are plain moves that never overwrite. review and
# out-of-vault always stay for the agent/user — automation never guesses.
# ---------------------------------------------------------------------------

EXECUTABLE_ACTIONS = ("trash", "inbox", "diary", "writings", "projects", "research", "wiki", "notes", "resources", "family", "plans")


def apply_routes(config: Config, results: list[dict]) -> list[dict]:
    """Execute safe routing decisions in place; annotate every item.

    Adds `executed` plus `to` (on success) or `skipped` (with a reason):
    conflict (target name exists), needs-agent (review), unsafe (out-of-vault),
    or no-op (keep)."""
    from .work import trash as work_trash

    applied: list[dict] = []
    for item in results:
        action = item["action"]
        if action == "keep":
            applied.append({**item, "executed": False, "skipped": "no-op"})
            continue
        if action == "trash":
            try:
                res = work_trash(config, item["path"])
                applied.append({**item, "executed": True, "to": res["to"]})
            except Exception as exc:  # protected path, trash conflict — report, never crash the batch
                applied.append({**item, "executed": False, "skipped": f"error: {exc}"})
            continue
        if action not in EXECUTABLE_ACTIONS:
            reason = "needs-agent" if action == "review" else "unsafe"
            applied.append({**item, "executed": False, "skipped": reason})
            continue
        target = item.get("target") or (config.dir(action) if action in config.directories else None)
        source = config.vault / item["path"]
        if target is None or not source.exists():
            applied.append({**item, "executed": False, "skipped": "error: 源或目标缺失"})
            continue
        dest_dir = config.vault / target
        dest = dest_dir / source.name
        if dest.exists():
            applied.append({**item, "executed": False, "skipped": f"conflict: {target}/{source.name} 已存在"})
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        source.rename(dest)
        applied.append({**item, "executed": True, "to": str(dest.relative_to(config.vault))})
    return applied
