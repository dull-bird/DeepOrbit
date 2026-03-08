#!/usr/bin/env python3
import os
import sys
import argparse
import re

def update_frontmatter(file_path, new_fields):
    """
    Safely reads a markdown file, parses its YAML frontmatter (if any),
    updates or adds the specified fields, and writes it back with proper spacing.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

    # Regex to cleanly extract frontmatter block and the rest of the body
    fm_pattern = re.compile(r'^---\n(.*?)\n---\n?', re.MULTILINE | re.DOTALL)
    match = fm_pattern.match(content)
    
    fm_dict = {}
    body = content
    
    if match:
        fm_content = match.group(1)
        body = content[match.end():]
        # Very basic YAML parsing for top-level key: value pairs
        for line in fm_content.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                fm_dict[key.strip()] = val.strip()
    else:
        # If no frontmatter exists but there's content, ensure body doesn't stick to our new YAML
        if content.lstrip().startswith('---'):
            print(f"Warning: {file_path} might have malformed frontmatter. Skipping to be safe.")
            return False
        body = content

    # Ensure body has at least one leading newline if it's not totally empty,
    # This specifically fixes the "---# Header" sticking issue the user experienced.
    if body and not body.startswith('\n'):
        body = '\n' + body

    # Update with new fields
    for k, v in new_fields.items():
        fm_dict[k] = v
        
    # Reconstruct the file
    new_fm_lines = ["---"]
    for k, v in fm_dict.items():
        # Handle string formatting for safety
        if isinstance(v, str) and (',' in v or '[' in v or ':' in v) and not (v.startswith('[') or v.startswith('"') or v.startswith("'")):
             new_fm_lines.append(f"{k}: \"{v}\"") # Quote strings with special yaml chars
        else:
             new_fm_lines.append(f"{k}: {v}")
    new_fm_lines.append("---")
    
    new_content = '\n'.join(new_fm_lines) + body # The body already has a leading newline from the fix above
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Robustly update Markdown Frontmatter")
    parser.add_argument("file_path", help="Path to the markdown file to edit")
    parser.add_argument("--set", action="append", help="Key=Value pair to set. Can be used multiple times. E.g. --set area=AI --set status=draft")
    
    args = parser.parse_args()
    
    if not args.set:
        print("No --set arguments provided. Nothing to do.")
        sys.exit(0)
        
    updates = {}
    for kv in args.set:
        if "=" in kv:
            k, v = kv.split("=", 1)
            updates[k.strip()] = v.strip()
            
    if update_frontmatter(args.file_path, updates):
        print(f"Successfully updated metadata for {args.file_path}")
    else:
        print(f"Failed to update metadata for {args.file_path}")
        sys.exit(1)
