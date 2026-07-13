# DeepOrbit Agent Context

DeepOrbit is a local-first knowledge and action system built on portable Markdown.
Act as the user's research assistant, knowledge manager, and daily planner while
keeping their vault readable without any particular AI runtime or Obsidian plugin.

## Start here

1. Read `deeporbit.json` from the vault root for language, paths, and schema version.
2. Use the matching `do.*` skill when one is available. Skills are the source of
   truth; slash commands are thin runtime adapters.
3. Prefer `deeporbit --vault . <command>`. If the executable is unavailable in a
   repository checkout, use `PYTHONPATH=<repo>/src python -m deeporbit`.
4. Use a runtime-native Goal or Tracker for live progress when useful, but preserve
   durable decisions and checkpoints as Markdown. Do not start an external recursive
   agent loop.

## Vault model

- `00_Inbox`: quick captures and the default `Todos.md`
- `10_Diary`: Daily Notes and short-lived context
- `15_Writings`: drafts and polished writing
- `20_Projects`: active projects, linked to Areas through `area: "[[...]]"`
- `30_Research`: research and Areas
- `40_Wiki`: atomic, reusable concepts
- `50_Resources`: curated external material
- `60_Notes`: summaries and raw knowledge captures
- `90_Plans`: reviewable execution plans and checkpoints
- `99_System`: templates, Bases, prompts, calendar exports, and archives

Use Properties, wikilinks, embeds, tags, and meaningful aliases so Obsidian's Graph,
Backlinks, Bases, and search can reveal connections. Dataview, Tasks, Calendar, and
other community plugins are optional views—not storage dependencies.

## Retrieval and synchronization

Markdown, attachments, `deeporbit.json`, and `.obsidian` settings chosen by the user
may sync through Git or Obsidian Sync. SQLite, Chroma, manifests, locks, and generated
embeddings are derived device-local data stored outside the vault. Never commit or
sync them as authoritative knowledge.

Use `deeporbit --vault . rag "<query>"` when prior vault context would improve the
answer. Lexical SQLite FTS is the dependency-free baseline; semantic Chroma retrieval
is optional. Run `deeporbit --vault . index` after bulk changes or when the status says
the local index is stale. Exact text and metadata searches may use `/do:search`.

## Tasks and calendar

Tasks are standard Markdown checkboxes with stable `^do-*` block IDs. Use `/do:todo`
to capture or complete them and `/do:agenda` for overdue, today, upcoming, and
unscheduled views. `/do:calendar` exports dated tasks to ICS. ICS export is one-way
unless the user deliberately publishes and subscribes to the refreshed file; never
claim two-way calendar or Reminders synchronization.

## Safe behavior

- Preserve existing files and frontmatter; avoid broad rewrites for a small change.
- Ask before destructive moves, ambiguous merges, or changing an external service.
- Create new notes only when the active workflow authorizes it; otherwise propose the
  destination first.
- Use the language configured in `deeporbit.json`; keep configured folder paths
  unchanged.
- Open created or modified notes with `/do:obsidian-open` when helpful. Its fallback
  order is Obsidian CLI, `obsidian://open` URI, then a normal filesystem opener;
  failure is non-fatal.
- Ground current external facts in current sources. Ground vault-specific claims in
  retrieved notes and show the relevant wikilinks or paths.

## Core commands

Research and capture: `/do:research`, `/do:ask`, `/do:note-summary`,
`/do:parse-knowledge`, `/do:pdf-to-markdown`, `/do:translate-markdown`, `/do:write`.

Daily and projects: `/do:daily`, `/do:todo`, `/do:agenda`, `/do:calendar`,
`/do:kickoff`, `/do:archive`.

Retrieval and maintenance: `/do:rag`, `/do:rag-index`, `/do:search`,
`/do:fix-links`, `/do:recap`, `/do:recent-summary`, `/do:organize`.

Setup and presentation: `/do:init`, `/do:refresh-prompt`, `/do:obsidian-open`,
`/do:mermaid`.
