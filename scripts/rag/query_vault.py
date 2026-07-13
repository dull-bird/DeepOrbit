#!/usr/bin/env python3
"""Compatibility wrapper for `deeporbit rag`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from deeporbit.config import load_config  # noqa: E402
from deeporbit.search import SearchIndex  # noqa: E402
from deeporbit.semantic import ChromaIndex  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Query a DeepOrbit vault.")
    parser.add_argument("vault_path")
    parser.add_argument("query")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--semantic", action="store_true")
    args = parser.parse_args()
    config = load_config(args.vault_path)
    index = SearchIndex(config)
    results = index.query(args.query, limit=args.top_k)
    if args.semantic:
        semantic = ChromaIndex(config)
        semantic.ensure(index.file_manifest())
        seen = {item["path"] for item in results}
        results.extend(item for item in semantic.query(args.query, limit=args.top_k) if item["path"] not in seen)
    print(json.dumps(results[: args.top_k], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
