#!/usr/bin/env python3
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Any

# Directories to ignore
IGNORE_DIRS: Set[str] = {'.git', 'node_modules', 'scripts', 'commands', 'skills', '.gemini', '99_System'}

def load_all_valid_basenames(vault_root: str) -> Set[str]:
    valid_names: Set[str] = set()
    for root, dirs, files in os.walk(vault_root):
        filtered_dirs = [d for d in dirs if d not in IGNORE_DIRS]
        dirs.clear()
        dirs.extend(filtered_dirs)
        for f in files:
            if f.endswith('.md'):
                valid_names.add(f[:-3])
    return valid_names

def find_ghost_links(content: str, valid_names: Set[str]) -> List[str]:
    wiki_link_pattern = re.compile(r'\[\[(.*?)\]\]')
    ghost_links: List[str] = []
    
    matches = wiki_link_pattern.findall(content)
    for match in matches:
        target = str(match).split('|')[0].split('#')[0].strip()
        if not target: continue
        
        if target not in valid_names:
            ghost_links.append(target)
            
    return ghost_links

def parse_frontmatter(content: str) -> List[str]:
    if not content.startswith('---'):
        return []
    
    end_idx = content.find('\n---\n', 3)
    if end_idx == -1:
        end_idx = content.find('\n---', 3)
        if end_idx == -1:
            return []
            
    frontmatter = content[3:end_idx].strip()
    keys: List[str] = []
    for line in frontmatter.split('\n'):
        if ':' in line:
            keys.append(line.split(':', 1)[0].strip())
    return keys

def analyze_vault(vault_root: str = '.') -> Dict[str, Any]:
    report: Dict[str, Any] = {
        'empty_folders': [],
        'orphan_files': [],
        'missing_metadata': [],
        'ghost_links': {}
    }
    
    valid_names = load_all_valid_basenames(vault_root)
    
    for root, dirs, files in os.walk(vault_root):
        filtered_dirs = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        dirs.clear()
        dirs.extend(filtered_dirs)
        
        if not dirs and not files and root != vault_root:
            report['empty_folders'].append(os.path.relpath(root, vault_root))
            
        rel_dir = os.path.relpath(root, vault_root)
        is_root = (rel_dir == '.')
        is_inbox = rel_dir.startswith('00_Inbox')
        
        for file in files:
            if not file.endswith('.md'): continue
            if file in ['README.md', 'Architecture.md', 'DeepOrbitPrompt.md']: continue
            
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, vault_root)
            
            if is_root or is_inbox:
                report['orphan_files'].append(rel_path)
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
                
            keys = parse_frontmatter(content)
            if not keys:
                report['missing_metadata'].append({
                    'file': rel_path,
                    'issue': 'No frontmatter found'
                })
            else:
                missing = [req for req in ['title', 'area', 'tags'] if req not in keys]
                if missing:
                    report['missing_metadata'].append({
                        'file': rel_path,
                        'issue': f"Missing fields: {', '.join(missing)}"
                    })
                    
            ghosts = find_ghost_links(content, valid_names)
            if ghosts:
                report['ghost_links'][rel_path] = ghosts
                
    return report

if __name__ == '__main__':
    vault_root = os.getcwd()
    print(json.dumps(analyze_vault(vault_root), indent=2, ensure_ascii=False))
