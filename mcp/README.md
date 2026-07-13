# DeepOrbit MCP server

The optional stdio server exposes deterministic local DeepOrbit capabilities to MCP clients.

## Tools

| Tool | Behavior |
|---|---|
| `deeporbit_status` | Vault, cache, CLI, Git, semantic backend, and optional plugin status |
| `rag_search` | Zero-dependency SQLite FTS retrieval |
| `rag_query` | Lexical retrieval plus optional Chroma semantic results |
| `task_agenda` | Read-only grouped Markdown tasks |

## Install

```bash
python3 -m pip install -e '.[mcp]'
```

Add the `rag` extra only when semantic retrieval is wanted:

```bash
python3 -m pip install -e '.[mcp,rag]'
```

## Run

```bash
DEEPORBIT_VAULT=/path/to/vault python3 mcp/deeporbit_rag/server.py
```

The repository `.mcp.json`, Kimi plugin, Gemini extension, and Codex plugin point to the same server. The MCP layer owns no state; it delegates to the Python Core and uses the OS cache for indexes.
