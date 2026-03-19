import os
import sys
import argparse
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

def main():
    parser = argparse.ArgumentParser(description="Query DeepOrbit vault using ChromaDB RAG.")
    parser.add_argument("vault_path", help="Path to the Obsidian vault")
    parser.add_argument("query", help="The semantic query to search for")
    parser.add_argument("--top_k", type=int, default=5, help="Number of chunks to return")
    args = parser.parse_args()

    vault_path = Path(args.vault_path).resolve()
    db_path = vault_path / ".deeporbit" / "chromadb"

    if not db_path.exists():
        print("Error: ChromaDB index not found. Please run the indexing script first by executing /do:rag-index.", file=sys.stderr)
        sys.exit(1)

    try:
        client = chromadb.PersistentClient(path=str(db_path))
        emb_fn = embedding_functions.DefaultEmbeddingFunction()
        collection = client.get_collection(name="deeporbit_notes", embedding_function=emb_fn)
    except Exception as e:
        print(f"Failed to load ChromaDB: {e}", file=sys.stderr)
        sys.exit(1)

    results = collection.query(
        query_texts=[args.query],
        n_results=args.top_k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    
    if not documents:
        print("No relevant notes found in the vault.")
        return

    print("### RAG Context Retrieved from Vault\n")
    for doc, meta in zip(documents, metadatas):
        file_path = meta.get("file_path", "Unknown")
        title = meta.get("title", "Unknown")
        print(f"**From Note: [[{title}]]** (Path: `{file_path}`)")
        print(f"```text\n{doc}\n```\n")

if __name__ == "__main__":
    main()
