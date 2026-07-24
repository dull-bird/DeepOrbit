from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .errors import DeepOrbitError


class GitSyncError(DeepOrbitError):
    code = "GIT_SYNC_ERROR"


@dataclass(slots=True)
class GitSyncResult:
    vault: str
    repo: bool
    git: bool
    pulled: bool
    committed: bool
    pushed: bool
    branch: str = ""
    remote: str = ""
    commit: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "vault": self.vault,
            "repo": self.repo,
            "git": self.git,
            "pulled": self.pulled,
            "committed": self.committed,
            "pushed": self.pushed,
            "branch": self.branch,
            "remote": self.remote,
            "commit": self.commit,
            "reason": self.reason,
        }


def _run_git(
    root: Path,
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=check,
        env=env,
    )


def _git_output(root: Path, *args: str) -> str:
    return _run_git(root, *args).stdout.strip()


def _git_identity(root: Path) -> dict[str, str]:
    name = _git_output(root, "config", "--get", "user.name") or "DeepOrbit"
    email = _git_output(root, "config", "--get", "user.email") or "deeporbit@local"
    return {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
    }


def _inside_repo(root: Path) -> bool:
    try:
        return _git_output(root, "rev-parse", "--is-inside-work-tree") == "true"
    except subprocess.CalledProcessError:
        return False


def _branch(root: Path) -> str:
    try:
        return _git_output(root, "rev-parse", "--abbrev-ref", "HEAD")
    except subprocess.CalledProcessError:
        return ""


def _remote(root: Path) -> str:
    remotes = _git_output(root, "remote")
    return remotes.splitlines()[0].strip() if remotes else ""


def _upstream_exists(root: Path) -> bool:
    try:
        _git_output(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        return True
    except subprocess.CalledProcessError:
        return False


def sync_vault(
    vault: Path | str,
    *,
    pull: bool = True,
    push: bool = True,
    message: str | None = None,
) -> GitSyncResult:
    root = Path(vault).expanduser().resolve()
    if not root.is_dir():
        raise GitSyncError(f"Vault does not exist: {root}")
    if shutil.which("git") is None:
        return GitSyncResult(vault=str(root), repo=False, git=False, pulled=False, committed=False, pushed=False, reason="git unavailable")
    if not _inside_repo(root):
        return GitSyncResult(vault=str(root), repo=False, git=True, pulled=False, committed=False, pushed=False, reason="not a git repo")

    branch = _branch(root)
    remote = _remote(root)
    result = GitSyncResult(vault=str(root), repo=True, git=True, pulled=False, committed=False, pushed=False, branch=branch, remote=remote)

    if pull and remote and branch and branch != "HEAD" and _upstream_exists(root):
        _run_git(root, "pull", "--rebase", "--autostash")
        result.pulled = True

    status = _git_output(root, "status", "--porcelain")
    if not status:
        result.reason = "clean"
        return result

    _run_git(root, "add", "-A")
    staged = _git_output(root, "diff", "--cached", "--name-only")
    if not staged:
        result.reason = "nothing staged"
        return result

    commit_message = message or f"DeepOrbit sync {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    _run_git(root, "commit", "-m", commit_message, env={**os.environ, **_git_identity(root)})
    result.committed = True
    result.commit = _git_output(root, "rev-parse", "--short", "HEAD")
    result.reason = commit_message

    if push and remote and branch and branch != "HEAD":
        if _upstream_exists(root):
            _run_git(root, "push")
        else:
            _run_git(root, "push", "-u", remote, "HEAD")
        result.pushed = True

    return result
