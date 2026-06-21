# DeepOrbit MCP servers (optional)

These are an **optional** modern alternative to shelling out to `scripts/rag/`.
They expose the vault's retrieval as native MCP tools, so an MCP-capable agent
(Claude Code, etc.) can call `rag_query` / `rag_search` directly.

> The skills work fine **without** this — `do.rag` and `do.search` still run the
> CLI scripts. Set up the MCP server only if you want native tool calls.

## `deeporbit-rag`

| Tool | What it does | Needs index? |
|------|--------------|--------------|
| `rag_query` | Semantic (vector) search over the ChromaDB index | Yes — run `/do:rag-index` first |
| `rag_search` | Exact string / regex search across note dirs | No |

### Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r mcp/deeporbit_rag/requirements.txt
```

### Register in Claude Code

The repo ships a project-scoped [`.mcp.json`](../.mcp.json). Point it at your vault
by exporting the vault path before launching your agent:

```bash
export DEEPORBIT_VAULT="$HOME/path/to/your/vault"
```

Or pass `vault_path` explicitly on each tool call. Verify with `/mcp` in Claude Code.

### Run standalone (debug)

```bash
DEEPORBIT_VAULT=~/vault python3 mcp/deeporbit_rag/server.py
```

> ⚠️ This server has not been exercised against a live ChromaDB index in CI —
> test `rag_query` against your own indexed vault before relying on it. The
> `rag_search` tool is index-free and self-contained.
