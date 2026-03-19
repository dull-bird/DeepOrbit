import os
import sys
import json
import argparse
import hashlib
from pathlib import Path
from tqdm import tqdm
import chromadb
from chromadb.utils import embedding_functions

# Directories to index
TARGET_DIRS = [
    "10_Diary",
    "20_Projects",
    "30_Research",
    "40_Wiki",
    "60_Notes",
]

# Simple Markdown chunker
def chunk_markdown(text, filename, max_chars=1200):
    chunks = []
    # Split by headers
    sections = text.split("\n## ")
    for i, section in enumerate(sections):
        if i > 0:
            section = "## " + section
        
        # If a section is too long, split by double newline
        if len(section) > max_chars:
            paragraphs = section.split("\n\n")
            current_chunk = ""
            for p in paragraphs:
                if len(current_chunk) + len(p) < max_chars:
                    current_chunk += p + "\n\n"
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = p + "\n\n"
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
        else:
            if section.strip():
                chunks.append(section.strip())
    
    # Filter out empty or very short chunks
    return [c for c in chunks if len(c) > 30]

def main():
    parser = argparse.ArgumentParser(description="Index DeepOrbit vault for semantic search using ChromaDB.")
    parser.add_argument("vault_path", help="Path to the Obsidian vault")
    args = parser.parse_args()

    vault_path = Path(args.vault_path).resolve()
    if not vault_path.is_dir():
        print(f"Error: Vault path {vault_path} does not exist.")
        sys.exit(1)

    deeporbit_dir = vault_path / ".deeporbit"
    os.makedirs(deeporbit_dir, exist_ok=True)

    db_path = deeporbit_dir / "chromadb"
    state_file = deeporbit_dir / "index_state.json"

    # Initialize ChromaDB
    # Using the default sentence-transformers model (all-MiniLM-L6-v2) which is fast and runs locally.
    print(f"Initializing ChromaDB at {db_path}...")
    client = chromadb.PersistentClient(path=str(db_path))
    emb_fn = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(name="deeporbit_notes", embedding_function=emb_fn)

    # Load existing state to skip unchanged files
    state = {}
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass

    files_to_index = []
    for d in TARGET_DIRS:
        target_path = vault_path / d
        if not target_path.is_dir():
            continue
        
        for root, _, files in os.walk(target_path):
            for file in files:
                if file.endswith(".md"):
                    full_path = Path(root) / file
                    mtime = os.path.getmtime(full_path)
                    rel_path = str(full_path.relative_to(vault_path))
                    
                    if rel_path not in state or state[rel_path] < mtime:
                        files_to_index.append((full_path, rel_path, mtime))
    
    if not files_to_index:
        print("Everything is up to date. No new notes to index.")
        return

    print(f"Found {len(files_to_index)} files to index/update...")
    
    for full_path, rel_path, mtime in tqdm(files_to_index):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Clean up old chunks for this file
            collection.delete(where={"file_path": rel_path})
            
            chunks = chunk_markdown(content, rel_path)
            if not chunks:
                state[rel_path] = mtime
                continue
                
            ids = [f"{hashlib.md5(c.encode()).hexdigest()}_{i}" for i, c in enumerate(chunks)]
            metadatas = [{"file_path": rel_path, "title": full_path.stem} for _ in chunks]
            
            collection.upsert(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            
            state[rel_path] = mtime
        except Exception as e:
            print(f"Error processing {rel_path}: {e}")

    # Save state
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print("Indexing complete!")

if __name__ == "__main__":
    main()
