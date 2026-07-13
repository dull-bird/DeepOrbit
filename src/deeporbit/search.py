from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import Config

INDEX_VERSION = 2


@dataclass(slots=True)
class FileState:
    size: int
    mtime_ns: int
    sha256: str


@dataclass(slots=True)
class IndexResult:
    added: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0


def _files(config: Config) -> list[Path]:
    files: list[Path] = []
    for rel in config.index_dirs:
        root = config.vault / rel
        if root.is_dir():
            files.extend(p for p in root.rglob("*.md") if not any(x.startswith(".") for x in p.relative_to(config.vault).parts))
    return sorted(set(files))


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@contextmanager
def _lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    try:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            # A crash must not leave a second computer or a later local session
            # permanently unable to rebuild a derived index.
            try:
                owner = int(path.read_text(encoding="utf-8").strip())
                os.kill(owner, 0)
            except (OSError, ValueError):
                path.unlink(missing_ok=True)
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            else:
                age = time.time() - path.stat().st_mtime
                if age > 60 * 60:
                    # PID reuse is rare, but an hour-old lock is never a useful
                    # reason to block a local, regenerable cache forever.
                    path.unlink(missing_ok=True)
                    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                else:
                    raise RuntimeError(f"Index is locked: {path}")
        os.write(fd, str(os.getpid()).encode())
        yield
    finally:
        if fd is not None:
            os.close(fd)
            path.unlink(missing_ok=True)


class SearchIndex:
    def __init__(self, config: Config):
        self.config = config
        self.cache = config.cache_dir
        self.db_path = self.cache / "search.sqlite"
        self.manifest_path = self.cache / "manifest.json"

    def _manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"version": INDEX_VERSION, "files": {}}
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if data.get("version") != INDEX_VERSION:
                return {"version": INDEX_VERSION, "files": {}}
            return data
        except (OSError, json.JSONDecodeError):
            return {"version": INDEX_VERSION, "files": {}}

    def _connection(self) -> sqlite3.Connection:
        self.cache.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.db_path)
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS notes USING fts5(path UNINDEXED, title, content)")
        return db

    def ensure(self) -> IndexResult:
        result = IndexResult()
        with _lock(self.cache / "index.lock"):
            old = self._manifest().get("files", {})
            current: dict[str, FileState] = {}
            changed: list[tuple[Path, str, bool]] = []
            for path in _files(self.config):
                rel = path.relative_to(self.config.vault).as_posix()
                stat = path.stat()
                previous = old.get(rel)
                if previous and previous.get("size") == stat.st_size and previous.get("mtime_ns") == stat.st_mtime_ns:
                    state = FileState(stat.st_size, stat.st_mtime_ns, previous["sha256"])
                    result.unchanged += 1
                else:
                    state = FileState(stat.st_size, stat.st_mtime_ns, _sha(path))
                    changed.append((path, rel, previous is not None))
                current[rel] = state
            deleted = sorted(set(old) - set(current))
            with self._connection() as db:
                for rel in deleted:
                    db.execute("DELETE FROM notes WHERE path = ?", (rel,))
                    result.deleted += 1
                for path, rel, existed in changed:
                    content = path.read_text(encoding="utf-8")
                    db.execute("DELETE FROM notes WHERE path = ?", (rel,))
                    db.execute("INSERT INTO notes(path, title, content) VALUES (?, ?, ?)", (rel, path.stem, content))
                    if existed:
                        result.updated += 1
                    else:
                        result.added += 1
            payload = {"version": INDEX_VERSION, "vault_id": self.config.vault_id, "files": {k: asdict(v) for k, v in current.items()}}
            tmp = self.manifest_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tmp.replace(self.manifest_path)
        return result

    def query(self, query: str, *, limit: int = 10) -> list[dict]:
        self.ensure()
        try:
            with self._connection() as db:
                rows = db.execute(
                    "SELECT path, title, snippet(notes, 2, '[', ']', ' … ', 28), bm25(notes) FROM notes WHERE notes MATCH ? ORDER BY bm25(notes) LIMIT ?",
                    (query, max(1, limit)),
                ).fetchall()
        except sqlite3.OperationalError:
            rows = []
            needle = query.casefold()
            for path in _files(self.config):
                content = path.read_text(encoding="utf-8")
                if needle in content.casefold():
                    rows.append((path.relative_to(self.config.vault).as_posix(), path.stem, content[:400], 0.0))
                    if len(rows) >= limit:
                        break
        return [{"path": p, "title": t, "snippet": s, "score": score} for p, t, s, score in rows]

    def status(self) -> dict:
        manifest = self._manifest()
        return {
            "cache": str(self.cache),
            "indexed_files": len(manifest.get("files", {})),
            "database_exists": self.db_path.exists(),
            "locked": (self.cache / "index.lock").exists(),
        }

    def file_manifest(self) -> dict[str, dict]:
        return self._manifest().get("files", {})
