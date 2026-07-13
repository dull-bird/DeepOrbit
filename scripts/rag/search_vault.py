#!/usr/bin/env python3
"""Compatibility wrapper for lexical DeepOrbit search."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from deeporbit.config import load_config  # noqa: E402
from deeporbit.search import SearchIndex  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Search a DeepOrbit vault using SQLite FTS.")
    parser.add_argument("vault_path")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(SearchIndex(load_config(args.vault_path)).query(args.query, limit=args.limit), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
