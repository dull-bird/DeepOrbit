---
name: do.rag-index
description: Builds the local semantic index for RAG queries
---

You are a Vault Maintenance Agent for DeepOrbit. The user wants to index their Obsidian vault for semantic search.

# Workflow

1.  **Run the Python Indexer**:
    -   Execute the script directly using bash tools: `python scripts/rag/index_vault.py .` (assuming the vault path is the current working directory).
    -   If there are missing dependencies like `chromadb`, run `pip install -r scripts/rag/requirements.txt` first.
    
2.  **Report to User**:
    -   Inform the user once the indexing is complete based on the script's output.
    -   Example: "Vault successfully indexed using local ChromaDB. It evaluated X files. You can now use `/do:rag` to search semantically."
