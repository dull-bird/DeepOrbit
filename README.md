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

### 1. Install only the connector globally

DeepOrbit's recommended cross-project install is **one global connector skill**:

```bash
npx skills add dull-bird/DeepOrbit --skill do.link --global --agent '*' --yes
```

Install the deterministic CLI once on the machine:

```bash
git clone https://github.com/dull-bird/DeepOrbit.git ~/src/DeepOrbit
python3 -m pip install -e ~/src/DeepOrbit
deeporbit __schema
```

`deeporbit __schema` prints the full machine-readable CLI surface for agents.
If the executable is unavailable from a checkout, use:

```bash
PYTHONPATH=~/src/DeepOrbit/src python -m deeporbit __schema
```

### 2. Initialize or take over a vault

```bash
deeporbit --vault ~/Documents/MyVault init --source ~/src/DeepOrbit
deeporbit --vault ~/Documents/MyVault doctor
deeporbit link add main ~/Documents/MyVault --description "Personal research and writing"
```

Initialization is idempotent. Existing notes and customized prompt files are
preserved. Legacy localized folders are merged only when safe; conflicts are
reported without overwriting either file. The initializer materializes:

- workflow skills into `99_System/DeepOrbit/skills/` plus `skills-index.json`;
- system templates, Bases, prompts, and methodology guides under `99_System/`;
- a curated portable repository bundle under `99_System/DeepOrbit/repo/`.

The bundle is not a Git checkout. It copies the runtime surface needed to use or
hand off the vault (skills, commands, prompts, hooks, CLI source, MCP, docs, and
manifests) while excluding `.git`, virtualenvs, caches, build outputs,
`node_modules`, and generated agent install artifacts.

### 3. Use it

```bash
deeporbit --vault ~/Documents/MyVault todo add "Review the paper" --today --due 2026-07-15
deeporbit --vault ~/Documents/MyVault agenda
deeporbit --vault ~/Documents/MyVault rag "index tracking"
deeporbit --vault ~/Documents/MyVault calendar export
deeporbit --vault ~/Documents/MyVault open 10_Diary/2026-07-15.md
```

You can also ask your agent naturally: “research index tracking”, “add this to today”, “what is overdue?”, or “find my previous notes about RAG”.

## Link vaults from any workspace

You do not need to install every skill into every project. Install only `do.link`, register one or more vaults, and route natural-language requests to them:

```bash
deeporbit link add main ~/Documents/MyVault --description "Personal research and writing"
deeporbit link add work ~/Documents/WorkVault --description "Work projects and client material"
deeporbit link list
deeporbit link route "prepare the client review"
deeporbit --vault @work todo add "Prepare the review" --today
deeporbit --vault @main rag "index tracking"
```

`link add` validates the target: `deeporbit` reports whether the folder was initialized, `obsidian_opened` whether Obsidian ever opened it (`.obsidian/app.json`). Descriptions drive routing — with several vaults the agent picks the target by matching your request against each vault's description, and `deeporbit link route` is the machine-level helper for ambiguous requests. The registry is device-local at `~/.config/deeporbit/links.json` and never syncs.

The CLI also experimentally supports [CLI Schema v1](https://github.com/cli-schema/cli-schema): `deeporbit __schema` prints a machine-readable description of the whole command tree for agent tooling.

## Work lifecycle, profile, and authorship

Every note with a `status:` field is a work item — not just `20_Projects`. The CLI owns every transition, so nothing depends on an agent remembering to move files:

```bash
deeporbit --vault ~/Documents/MyVault status                              # active / paused / done / archived, vault-wide
deeporbit --vault ~/Documents/MyVault pause 30_Research/Old-Thread.md     # dormant but visible
deeporbit --vault ~/Documents/MyVault resume 30_Research/Old-Thread.md
deeporbit --vault ~/Documents/MyVault done 15_Writings/essay.md
deeporbit --vault ~/Documents/MyVault archive 20_Projects/BigProj         # folder + assets, never overwrites
deeporbit --vault ~/Documents/MyVault trash 00_Inbox/stale.md             # reversible, into .trash/
```

`99_System/Bases/Work Status.base` is the standing board for active / paused / done / archived work. `99_System/Profile.md` is the vault's picture of the user: stable facts through `profile set`, durable learnings through `profile observe` (timestamped, source-tagged, user-authored facts never silently overwritten).

Folders managed by an external sync (e.g. `60_Notes/微信读书` exported by [weread-vault](https://github.com/dull-bird/weread-vault)) are **read-only zones**: `deeporbit init` detects them via sync frontmatter and records them in `deeporbit.json` (`readonly.directories`). The lifecycle CLI refuses to mutate them, `status` marks them, and suggestions skip them — link to these notes, derive analysis elsewhere.

Authorship is one invisible frontmatter field, never a visible badge: agents **must** write `author: ai` on every note they create and `author: mixed` when substantially rewriting a human note. Unmarked notes are human — the user never tags anything. Reading view stays clean, and Bases can filter AI output from human writing.

## Guidance, rhythm, and extensibility

- `deeporbit --vault ~/Documents/MyVault suggest` — prioritized issues derived from vault state (done-not-archived, dormant projects, stale index, empty profile…).
- `/do:mentor` — a coach, not an assistant: diagnoses from `status` + `suggest` + profile, teaches one method slice at a time (GTD for commitments, PARA for filing, Zettelkasten for knowledge, Atomic Habits for rhythm — boundaries researched in [docs/methodology.md](docs/methodology.md), materialized into each vault), and leaves you with one next action.
- `/do:dream` — the vault's offline consolidation: promotes repeated themes to Wiki, finds hidden connections, nudges lifecycle decisions, records profile observations. It proposes; you approve.
- `deeporbit cron add dream "Run the do.dream consolidation workflow" --every daily` — device-local schedules; `cron run-due` reports what's due for your agent runtime or system cron.
- `deeporbit --vault . sync` — git sync for the current vault (pull, commit, push when needed). Use it directly or via `deeporbit cron`.

- **Recipes** (`99_System/Recipes/*.md`) are the extension point: declarative `cli:` / `skill:` / `note:` steps composing DeepOrbit with any other skill. `deeporbit --vault . recipe run "Weekly Review"` resolves one into an execution plan. Prefer a recipe over new infrastructure.

The tooling research behind these choices (PDF/Markdown/HTML processors, the Obsidian plugin ecosystem, community AI-note projects like kepano's obsidian-skills) is in [docs/tooling-landscape.md](docs/tooling-landscape.md).

## Obsidian plugin

`plugin/` ships a thin, LLM-free Obsidian companion: a work-status sidebar (active / paused / done / archived with one-click transitions and AI/human markers) plus pause / resume / done / archive commands with the same no-overwrite semantics as the CLI. See [plugin/README.md](plugin/README.md).

## Web dashboard

```bash
deeporbit --vault ~/Documents/MyVault serve --open        # http://127.0.0.1:8765
```

A local, zero-dependency dashboard (binds 127.0.0.1 only): status cards and dormant counts, a 14-week activity heatmap, prioritized suggestions, the full work-item table with one-click pause/resume/done/archive, status/authorship/directory statistics, vault-wide search, recipes and cron overviews — plus an **Agent panel that chats through ACP** (`omp acp`, `claude --acp`, `gemini --acp` auto-detected, `--agent` to pick one). Agent file reads are sandboxed to the vault; write requests are denied. The UI follows Apple's fluid-interface principles (translucent materials, instant pointer feedback, reduced-motion fallbacks).

## Runtime compatibility

| Runtime | Portable Skills | Native package | Commands | MCP | Optional hooks | Prompt/context loading | Long-work enhancement |
|---|---:|---|---:|---:|---:|---|---|
| Kimi Code | Yes | `kimi.plugin.json` | Yes | Yes | Yes | Runtime hook + prompt file | Experimental Goal + checkpoints |
| OpenClaw | Yes | Workspace `.agents/skills` | Natural language | Yes | Yes | Runtime-dependent | Native Goal + checkpoints |
| Gemini / Antigravity | Yes | `gemini-extension.json` | Yes | Yes | Yes | `contextFileName` + hook | Plan/Tracker + checkpoints |
| Claude Code | Yes | `.claude-plugin/plugin.json` | Yes | Yes | Yes | `CLAUDE.md` imports `DeepOrbitPrompt.md` | Markdown checkpoints |
| Codex | Yes | `.codex-plugin/plugin.json` | Skills/natural language | Yes | Yes | Trusted `.codex/hooks` or plugin hook | Markdown checkpoints |
| OMP | Yes | — | Runtime-dependent | Optional | Yes | Native `.omp/hooks/pre/deeporbit.ts` | Markdown checkpoints |
| Other Agent Skills runtimes | Yes | — | Runtime-dependent | Optional | — | Runtime-dependent | Markdown checkpoints |

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

DeepOrbit 2.0 ships **29 `do.*` skills**. `skills/` is the single source of truth; every skill has paired Claude-style Markdown and Gemini TOML commands.

| Skill | Purpose |
|---|---|
| `do.init` | Safely initialize or upgrade a vault |
| `do.link` | Link external vaults and route requests to their workflows |
| `do.mentor` | Coach on methods, tools, and recipes; diagnose vault health |
| `do.dream` | Offline consolidation: promotions, connections, lifecycle nudges |
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

`tests/fixture_vault.py` builds a messy example vault (active/paused/done projects, legacy localized folders, AI- and human-authored notes, a LaTeX fixture). The integration suite drives it end to end: initialization and migration, lifecycle transitions, archiving, trash protection, the todo → agenda → calendar chain, index synchronization on add/modify/delete, link routing, user profile maintenance, and the LaTeX splitter.

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
