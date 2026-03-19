import os
import sys
import re
import argparse
from pathlib import Path

# Directories to search
TARGET_DIRS = [
    "10_Diary",
    "20_Projects",
    "30_Research",
    "40_Wiki",
    "50_Resources",
    "60_Notes",
]

def main():
    parser = argparse.ArgumentParser(description="Exact and regex search across DeepOrbit vault.")
    parser.add_argument("vault_path", help="Path to the Obsidian vault")
    parser.add_argument("query", help="The exact string or regex pattern to search for")
    parser.add_argument("--case-sensitive", action="store_true", help="Enable case-sensitive search")
    args = parser.parse_args()

    vault_path = Path(args.vault_path).resolve()
    if not vault_path.is_dir():
        print(f"Error: Vault path {vault_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    flags = 0 if args.case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(args.query, flags=flags)
    except re.error as e:
        print(f"Invalid regex pattern: {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    
    for d in TARGET_DIRS:
        target_path = vault_path / d
        if not target_path.is_dir():
            continue
            
        for root, _, files in os.walk(target_path):
            for file in files:
                if file.endswith(".md"):
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(vault_path))
                    
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            
                        file_matches = []
                        for i, line in enumerate(lines):
                            if pattern.search(line):
                                file_matches.append((i + 1, line.strip()))
                                
                        if file_matches:
                            results.append({
                                "file": rel_path,
                                "title": full_path.stem,
                                "matches": file_matches
                            })
                    except Exception as e:
                        print(f"Error reading {rel_path}: {e}", file=sys.stderr)

    if not results:
        print(f"No exact matches found for: '{args.query}'")
        return

    print(f"### Exact Search Results for '{args.query}'\n")
    for res in results:
        print(f"**From Note: [[{res['title']}]]** (Path: `{res['file']}`)")
        print("```text")
        for line_num, content in res["matches"]:
            # Truncate very long lines for display
            if len(content) > 150:
                content = content[:150] + "..."
            print(f"L{line_num}: {content}")
        print("```\n")

if __name__ == "__main__":
    main()
