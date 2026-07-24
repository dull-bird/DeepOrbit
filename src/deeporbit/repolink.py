"""Canonical external-repo pointer notes.

A vault that syncs across machines must record *where* code lives, not just
*that* it lives elsewhere. The pointer format is fixed — same repo, same note,
every time:

    type: repo · repo · host · user · os · github?

Generated only through this module so no agent improvises a new shape.
"""

from __future__ import annotations

import getpass
import platform
import socket
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import Config
from .errors import DeepOrbitError


class RepoLinkError(DeepOrbitError):
    code = "REPO_LINK_ERROR"


@dataclass(slots=True)
class MachineInfo:
    host: str
    user: str
    os: str


def machine_info() -> MachineInfo:
    system = platform.system().lower()
    os_name = {"darwin": "macos"}.get(system, system)
    return MachineInfo(host=socket.gethostname(), user=getpass.getuser(), os=f"{os_name} {platform.release()}")


def render_pointer(repo: Path, title: str, *, github: str = "", today: date | None = None) -> str:
    info = machine_info()
    today = today or date.today()
    remote = f"\ngithub: {github}" if github else ""
    remote_line = f"\n- **远端**：{github}" if github else "\n- **远端**：暂无（仅此机器）"
    return f"""---
type: repo
repo: {repo}
host: {info.host}
user: {info.user}
os: {info.os}{remote}
created: {today.isoformat()}
---

# {title}

代码不在 vault 里（原则：vault 只放指针）。

- **仓库**：`{repo}`
- **机器**：{info.host}
- **用户**：{info.user}
- **系统**：{info.os}{remote_line}

在别的电脑上使用：先确认该机器上路径 `{repo}` 是否存在；不存在则从远端克隆，或回到 **{info.host}** 操作。
"""


def write_pointer(config: Config, repo_path: str, note_rel: str, title: str, *, github: str = "") -> dict:
    remote_only = repo_path.startswith(("http://", "https://"))
    if remote_only:
        repo = repo_path.rstrip("/")
        github = github or repo
    else:
        repo = Path(repo_path).expanduser().resolve()
        if not repo.is_dir():
            raise RepoLinkError(f"Repo does not exist: {repo}")
    note = config.vault / note_rel
    if note.suffix != ".md":
        raise RepoLinkError(f"Pointer must be a .md note: {note_rel}")
    if note.exists():
        raise RepoLinkError(f"Pointer note already exists, nothing overwritten: {note_rel}")
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(render_pointer(Path(repo) if not remote_only else repo, title, github=github), encoding="utf-8")
    return {"note": note_rel, "repo": str(repo), "host": machine_info().host}
