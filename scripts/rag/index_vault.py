#!/usr/bin/env python3
"""Compatibility wrapper for `deeporbit index ensure`."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from deeporbit.config import load_config  # noqa: E402
from deeporbit.search import SearchIndex  # noqa: E402
from deeporbit.semantic import ChromaIndex  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or update a DeepOrbit local search index.")
    parser.add_argument("vault_path")
    parser.add_argument("--semantic", action="store_true")
    args = parser.parse_args()
    config = load_config(args.vault_path)
    index = SearchIndex(config)
    output = {"lexical": asdict(index.ensure())}
    if args.semantic:
        output["semantic"] = asdict(ChromaIndex(config).ensure(index.file_manifest()))
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
