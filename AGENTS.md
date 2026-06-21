# DeepOrbit — Agent Guide

DeepOrbit is a **portable Agent Skills pack**. It turns an [Obsidian](https://obsidian.md/)
vault into an automated deep-research and personal-knowledge-management engine. The
skills are tool-neutral and run on any agent that supports the Agent Skills standard
(Claude Code, Cursor, Codex, Windsurf, Gemini CLI, …).

## Repository layout

```
skills/            # SINGLE SOURCE OF TRUTH — one folder per skill, each with SKILL.md
  do.<name>/SKILL.md
  do.<name>/scripts/      # optional bundled scripts (e.g. do.pdf-to-markdown)
  do.<name>/reference/    # optional progressive-disclosure detail (e.g. do.mermaid)
commands/do/*.md   # Claude Code slash commands -> /do:<name>
commands/do/*.toml # Gemini CLI slash commands (same names; compat layer)
mcp/               # optional MCP servers (deeporbit-rag: rag_query / rag_search)
scripts/           # shared repo scripts (vault init, RAG indexer, news fetch)
docs/              # design notes / proposals (not shipped inside skills)
.claude-plugin/    # Claude Code plugin + marketplace manifests
.mcp.json          # project-scoped MCP registration
DeepOrbitPrompt.md # the system prompt injected into the user's vault
```

When you add a skill, mirror it in **both** `commands/do/<name>.md` (Claude) and
`commands/do/<name>.toml` (Gemini) so the `/do:<name>` slash command exists on both runtimes.

Long, reference-heavy skills should keep `SKILL.md` lean and push catalogs/examples into a
sibling `reference/` file (progressive disclosure) — see `skills/do.mermaid/`.

Do **not** commit per-tool install directories (`.agents/`, `.claude/skills/`,
`.cursor/`, `.roo/`, …) or `skills-lock.json` — those are generated when a *consumer*
runs `npx skills add`. They are git-ignored.

## Skill authoring conventions

- Each skill lives in `skills/do.<name>/SKILL.md` with YAML frontmatter:
  `name`, `description`, and optional `license` / `metadata`.
- `name` MUST match the directory name (`do.<name>`).
- `description` is the trigger signal — write it for *when to use*, not just what it is.
- Keep `SKILL.md` lean; push long references/examples into sibling files and link them
  (progressive disclosure). Bundle executable helpers under the skill's `scripts/`.

## Project rules (for agents editing this repo)

### README sync
When modifying `README.md` or `README_CN.md`, you **MUST** update both. `README.md` is
English, `README_CN.md` is Chinese; any content change to one must be mirrored in the other.

### Skill & command sync
When adding, removing, or modifying any skill (`skills/`) or command (`commands/`), you
**MUST** update `README.md` and `README_CN.md` — skill counts, mindmap diagrams, and the
quick-reference table.
