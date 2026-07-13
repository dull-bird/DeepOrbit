from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .config import Config


def chunk_markdown(text: str, *, max_chars: int = 1600) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if length and length + len(paragraph) + 2 > max_chars:
            chunks.append("\n\n".join(current))
            current, length = [], 0
        if len(paragraph) > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current, length = [], 0
            chunks.extend(paragraph[i : i + max_chars] for i in range(0, len(paragraph), max_chars))
        else:
            current.append(paragraph)
            length += len(paragraph) + 2
    if current:
        chunks.append("\n\n".join(current))
    return [chunk for chunk in chunks if len(chunk) >= 30]


@dataclass(slots=True)
class SemanticResult:
    indexed_files: int
    deleted_files: int
    chunks: int


class ChromaIndex:
    collection_name = "deeporbit_notes_v2"

    def __init__(self, config: Config):
        self.config = config
        self.cache = config.cache_dir / "chromadb"
        self.manifest = config.cache_dir / "semantic_manifest.json"

    @staticmethod
    def available() -> bool:
        try:
            import chromadb  # noqa: F401
            return True
        except ImportError:
            return False

    def _collection(self):
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError as exc:
            raise RuntimeError("ChromaDB is optional. Install DeepOrbit with the 'rag' extra.") from exc
        client = chromadb.PersistentClient(path=str(self.cache))
        return client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=embedding_functions.DefaultEmbeddingFunction(),
        )

    def ensure(self, file_manifest: dict[str, dict]) -> SemanticResult:
        old: dict[str, str] = {}
        if self.manifest.exists():
            try:
                old = json.loads(self.manifest.read_text(encoding="utf-8")).get("files", {})
            except (OSError, json.JSONDecodeError):
                old = {}
        current = {path: state["sha256"] for path, state in file_manifest.items()}
        changed = [path for path, sha in current.items() if old.get(path) != sha]
        deleted = sorted(set(old) - set(current))
        collection = self._collection()
        total_chunks = 0
        for rel in [*deleted, *changed]:
            collection.delete(where={"file_path": rel})
        for rel in changed:
            content = (self.config.vault / rel).read_text(encoding="utf-8")
            chunks = chunk_markdown(content)
            if not chunks:
                continue
            file_hash = current[rel]
            ids = [hashlib.sha256(f"{rel}\0{file_hash}\0{i}".encode()).hexdigest() for i in range(len(chunks))]
            collection.upsert(
                ids=ids,
                documents=chunks,
                metadatas=[{"file_path": rel, "title": Path(rel).stem, "ordinal": i} for i in range(len(chunks))],
            )
            total_chunks += len(chunks)
        self.manifest.write_text(json.dumps({"version": 1, "files": current}, indent=2) + "\n", encoding="utf-8")
        return SemanticResult(len(changed), len(deleted), total_chunks)

    def query(self, query: str, *, limit: int = 5) -> list[dict]:
        collection = self._collection()
        result = collection.query(query_texts=[query], n_results=max(1, limit))
        docs = result.get("documents", [[]])[0]
        metadata = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            {
                "path": meta.get("file_path", ""),
                "title": meta.get("title", ""),
                "snippet": doc,
                "score": distance,
                "backend": "semantic",
            }
            for doc, meta, distance in zip(docs, metadata, distances)
        ]
