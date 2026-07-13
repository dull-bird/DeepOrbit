# DeepOrbit

![DeepOrbit](deeporbit.png)

> A local-first Obsidian knowledge system that works across Kimi Code, OpenClaw, Gemini/Antigravity, Codex, and other Agent Skills runtimes.

[中文](README_CN.md) · [Documentation](https://dull-bird.github.io/DeepOrbit/) · [Architecture](docs/architecture.md)

DeepOrbit keeps research, projects, writing, tasks, and retrieval in ordinary local files. Agent Skills describe workflows; a small Python core handles deterministic operations such as safe initialization, incremental search, task IDs, and calendar export. Native goals, hooks, plugins, and MCP improve each runtime without becoming required for correctness.

## Why DeepOrbit

- **Portable:** the same `skills/` work across Agent Skills runtimes.
- **Local-first:** Markdown is authoritative; no DeepOrbit cloud account is required.
- **Sync-neutral:** use Git, Obsidian Sync, or any filesystem sync. Search indexes rebuild locally.
- **Obsidian-native:** Properties, Bases, Graph, Backlinks, Daily Notes, Callouts, and Canvas remain useful outside an agent.
- **Graceful fallback:** ChromaDB, MCP, Obsidian CLI, Tasks, Dataview, and Calendar are optional.
- **Checkpointed:** long work resumes from Markdown checklists instead of an external self-invoking loop.

## Three-minute tutorial

### 1. Install the portable Skills

```bash
npx skills add dull-bird/DeepOrbit
```

Or clone the repository and install the deterministic core:

```bash
git clone https://github.com/dull-bird/DeepOrbit.git
cd DeepOrbit
python3 -m pip install -e .
```

### 2. Initialize a vault

```bash
deeporbit --vault ~/Documents/MyVault init
deeporbit --vault ~/Documents/MyVault doctor
```

Initialization is idempotent. Existing notes and customized prompt files are preserved. Legacy localized folders are merged only when safe; conflicts are reported without overwriting either file.

### 3. Use it

```bash
deeporbit --vault ~/Documents/MyVault todo add "Review the paper" --today --due 2026-07-15
deeporbit --vault ~/Documents/MyVault agenda
deeporbit --vault ~/Documents/MyVault rag "index tracking"
deeporbit --vault ~/Documents/MyVault calendar export
deeporbit --vault ~/Documents/MyVault open 10_Diary/2026-07-15.md
```

You can also ask your agent naturally: “research index tracking”, “add this to today”, “what is overdue?”, or “find my previous notes about RAG”.

## Runtime compatibility

| Runtime | Portable Skills | Native package | Commands | MCP | Optional hooks | Long-work enhancement |
|---|---:|---|---:|---:|---:|---|
| Kimi Code | Yes | `kimi.plugin.json` | Yes | Yes | Yes | Experimental Goal + checkpoints |
| OpenClaw | Yes | Workspace `.agents/skills` | Natural language | Yes | Yes | Native Goal + checkpoints |
| Gemini / Antigravity | Yes | `gemini-extension.json` | Yes | Yes | Yes | Plan/Tracker + checkpoints |
| Codex | Yes | `.codex-plugin/plugin.json` | Yes | Yes | Yes | Thread Goal + checkpoints |
| Other Agent Skills runtimes | Yes | — | Runtime-dependent | Optional | — | Markdown checkpoints |

The runtime feature is never the only place progress is stored. Long workflows write a plan with checked and unchecked items under `90_Plans/` and can resume after interruption or on another agent.

## Sync and local retrieval

Only notes, templates, Bases, and `deeporbit.json` belong in the vault. Machine-local indexes live under the operating system cache directory, keyed by the stable vault ID.

```text
Git / Obsidian Sync             Each computer
Markdown + deeporbit.json  -->  ~/.cache/deeporbit/<vault-id>/
                                  search.sqlite
                                  manifest.json
                                  optional chromadb/
```

Every retrieval checks for added, changed, renamed, and deleted files before querying. The default SQLite FTS index has no third-party dependencies. Optional semantic retrieval is available with:

```bash
python3 -m pip install -e '.[rag]'
deeporbit --vault ~/Documents/MyVault index ensure --semantic
deeporbit --vault ~/Documents/MyVault rag "a conceptual query" --semantic
```

Do not commit or synchronize vector databases. See [Sync and RAG](docs/sync-and-rag.md).

## Obsidian integration

DeepOrbit ships native Bases for projects, research, task-containing notes, and knowledge health under `99_System/Bases/`.

Core Obsidian features:

- Properties provide a shared schema (`type`, `status`, `area`, `created`, `updated`, `tags`).
- Bases provide editable file-level dashboards.
- Graph and Backlinks expose conceptual relationships and orphans.
- Daily Notes connect agenda, recap, and current work.
- Canvas is available for spatial research maps when it improves understanding.

Optional community plugins:

| Plugin | Enhancement | Required? |
|---|---|---:|
| Tasks | Rich task queries and completion UI | No |
| Dataview | Advanced read-only dashboards | No |
| Calendar | Daily Note navigation | No |

Obsidian CLI is preferred for opening generated notes. DeepOrbit falls back to `obsidian://` URIs and then to printing the absolute path.

## Tasks, agenda, and calendar

Tasks remain portable Markdown:

```markdown
- [ ] Review DeepOrbit architecture #task ⏳ 2026-07-13 📅 2026-07-15 ^do-20260713120000-a1b2c3
```

The stable block ID supports exact completion and stable iCalendar UIDs. ICS export is a local snapshot with alarms; it does not claim two-way Google or Apple Calendar synchronization. See [Tasks and calendar](docs/todo-calendar.md).

## Skill catalog

DeepOrbit 2.0 ships **26 `do.*` skills**. `skills/` is the single source of truth; every skill has paired Claude-style Markdown and Gemini TOML commands.

| Skill | Purpose |
|---|---|
| `do.init` | Safely initialize or upgrade a vault |
| `do.daily` | Daily planning, recap, news, and project context |
| `do.todo` | Capture, list, and complete Markdown tasks |
| `do.agenda` | Group overdue, today, upcoming, and unscheduled tasks |
| `do.calendar` | Export dated tasks to portable ICS |
| `do.kickoff` | Turn an idea into a structured project |
| `do.write` | Polish raw thoughts into personal writing |
| `do.research` | Checkpointed evidence-based deep research |
| `do.ask` | Lightweight vault-aware Q&A |
| `do.brainstorm` | Interactive idea exploration |
| `do.rag` | Self-refreshing local retrieval |
| `do.rag-index` | Inspect and refresh lexical or semantic indexes |
| `do.search` | Fast lexical and phrase search |
| `do.note-summary` | Full-source summaries and captures |
| `do.parse-knowledge` | Convert unstructured material into durable notes |
| `do.recap` | Summarize recent vault changes |
| `do.arxiv-translator` | Translate and compile arXiv LaTeX sources |
| `do.pdf-to-markdown` | Checkpointed high-fidelity PDF conversion |
| `do.translate-markdown` | Complete, glossary-consistent Markdown translation |
| `do.translate` | Route document translation to the right workflow |
| `do.mermaid` | Select and create suitable Mermaid diagrams |
| `do.fix-links` | Find and resolve ghost wikilinks |
| `do.organize` | Analyze and safely reorganize a vault |
| `do.archive` | Archive completed projects and processed items |
| `do.refresh-prompt` | Merge upstream prompt changes without losing customizations |
| `do.obsidian-open` | Open notes through CLI, URI, or path fallback |

## MCP tools

The optional server exposes:

- `deeporbit_status`
- `rag_search`
- `rag_query`
- `task_agenda`

Install with `python3 -m pip install -e '.[mcp]'`. Lexical retrieval works without ChromaDB. See [MCP reference](mcp/README.md).

## Development

```bash
python3 -m pip install -e '.[dev]'
python3 -m unittest discover -s tests -v
python3 scripts/validate_repo.py
npm --prefix site install
npm --prefix site run build
```

CI validates Python behavior, skills and commands, JSON manifests, shell syntax, runtime profiles, and the GitHub Pages build. When changing a skill or command, update both README files as required by [AGENTS.md](AGENTS.md).

## Documentation map

- Tutorial: [Getting started](docs/getting-started.md)
- How-to: [Sync and rebuild RAG](docs/sync-and-rag.md)
- How-to: [Tasks and calendar](docs/todo-calendar.md)
- Reference: [Runtime compatibility](docs/runtime-compatibility.md)
- Explanation: [Architecture](docs/architecture.md)

## Acknowledgments

DeepOrbit was inspired by [OrbitOS](https://github.com/MarsWang42/OrbitOS) and uses ideas from the portable Agent Skills ecosystem. See [skills/ACKNOWLEDGMENTS.md](skills/ACKNOWLEDGMENTS.md).

## License

[MIT](LICENSE)
