#!/usr/bin/env python3
import os
import re
import json
from pathlib import Path

# Directories to ignore
IGNORE_DIRS = {'.git', 'node_modules', 'scripts', 'commands', 'skills', '.gemini', '99_系统'}

# Roots that matter most for content
CONTENT_ROOTS = {'40_知识库', '20_项目', '00_收件箱', '30_领域', '10_看板', '50_资源'}

def load_all_valid_basenames(vault_root):
    """Load all valid markdown file basenames (without extension) to resolve wikilinks."""
    valid_names = set()
    for root, dirs, files in os.walk(vault_root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.endswith('.md'):
                valid_names.add(f[:-3])
    return valid_names

def find_ghost_links(content, valid_names):
    """Find [[Links]] that do not exist."""
    # Matches [[Link]] or [[Link|Alias]] or [[Link#Heading]]
    wiki_link_pattern = re.compile(r'\[\[(.*?)\]\]')
    ghost_links = []
    
    matches = wiki_link_pattern.findall(content)
    for match in matches:
        # Extract the actual link target (ignore alias or heading)
        target = match.split('|')[0].split('#')[0].strip()
        if not target: continue
        
        if target not in valid_names:
            ghost_links.append(target)
            
    return ghost_links

def parse_frontmatter(content):
    """Basic frontmatter parser to check for required fields."""
    if not content.startswith('---'):
        return None
    
    end_idx = content.find('\n---\n', 3)
    if end_idx == -1:
        end_idx = content.find('\n---', 3)
        if end_idx == -1:
            return None
            
    frontmatter = content[3:end_idx].strip()
    keys = []
    for line in frontmatter.split('\n'):
        if ':' in line:
            keys.append(line.split(':', 1)[0].strip())
    return keys

def analyze_vault(vault_root='.'):
    report = {
        'empty_folders': [],
        'orphan_files': [],
        'missing_metadata': [],
        'ghost_links': {}
    }
    
    valid_names = load_all_valid_basenames(vault_root)
    
    for root, dirs, files in os.walk(vault_root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        # Check empty folders
        if not dirs and not files and root != vault_root:
            report['empty_folders'].append(os.path.relpath(root, vault_root))
            
        rel_dir = os.path.relpath(root, vault_root)
        is_root = (rel_dir == '.')
        is_inbox = rel_dir.startswith('00_收件箱')
        
        for file in files:
            if not file.endswith('.md'): continue
            if file in ['README.md', 'Architecture.md', 'DeepOrbitPrompt.md']: continue
            
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, vault_root)
            
            # Check Orphans
            if is_root or is_inbox:
                report['orphan_files'].append(rel_path)
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
                
            # Check Metadata
            keys = parse_frontmatter(content)
            if keys is None:
                report['missing_metadata'].append({
                    'file': rel_path,
                    'issue': 'No frontmatter found'
                })
            else:
                missing = []
                for required in ['title', 'area', 'tags']:
                    if required not in keys:
                        missing.append(required)
                if missing:
                    report['missing_metadata'].append({
                        'file': rel_path,
                        'issue': f"Missing fields: {', '.join(missing)}"
                    })
                    
            # Check Ghost Links
            ghosts = find_ghost_links(content, valid_names)
            if ghosts:
                report['ghost_links'][rel_path] = ghosts
                
    return report

if __name__ == '__main__':
    vault_root = os.getcwd()
    report = analyze_vault(vault_root)
    print(json.dumps(report, indent=2, ensure_ascii=False))
