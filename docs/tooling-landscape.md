# Tooling Landscape — What DeepOrbit Should Adopt Next

> Design note. Researched 2026-07-21 via current public sources (GitHub,
> official docs, benchmarks). DeepOrbit constraints: local-first, zero runtime
> dependencies in the core, workflows expressed as Agent Skills, vault = plain
> Markdown + frontmatter + Obsidian Bases.

## 1. PDF → Markdown

| Tool | Approach | License | Notes |
|---|---|---|---|
| [Docling](https://arxiv.org/pdf/2501.17887v1) (IBM) | pipeline w/ layout models | MIT | Strong tables/structure, active, docs excellent |
| [Marker](https://ai.gopubby.com/pdf-to-markdown-conversion-benchmark-part-3-01c22dce8e9d) (VikParuchuri) | model pipeline | GPL-3.0 (commercial option) | Top fidelity on papers; heavier deps (torch) |
| [MinerU](https://github.com/opendatalab/MinerU) | model pipeline | AGPL-3.0 | Excellent on dense academic PDFs; GPU-friendly |
| [pymupdf4llm](https://arxiv.org/pdf/2409.05137) | bytecode parse | AGPL/commercial | Fastest for digital-born PDFs; no OCR |
| pdfplumber / pypdf | pure-python parse | MIT / Apache-2.0 | Lightweight; weak layout |
| [GROBID](https://www.s-anand.net/blog/lists/tools/) | TEI/XML references | Apache-2.0 | De-facto for citations/reference extraction |

Benchmark consensus ([LlamaIndex eval](https://www.llamaindex.ai/insights/ocr-to-markdown-evaluation),
[gopubby benchmark](https://ai.gopubby.com/pdf-to-markdown-conversion-benchmark-part-3-01c22dce8e9d),
[READOC](https://arxiv.org/pdf/2409.05137)): model-pipeline tools (Marker,
MinerU, Docling) beat parsers on scanned/academic PDFs; pymupdf4llm wins on
speed for clean digital PDFs.

**Fit:** DeepOrbit's `do.pdf-to-markdown` is agent-driven and already
tool-agnostic. The gap is a *deterministic fallback* for batch jobs.
**Adopt:** Docling as an optional extra (`pip install deeporbit[pdf]`) behind
the skill — MIT, CPU-only mode, active governance. Keep pymupdf4llm as the
speed path when present. Skip GROBID unless citation graphs become a goal.

## 2. Markdown processing

- **mistune / markdown-it-py** — fast CommonMark parsers; mistune is the most
  embed-friendly for a future note-graph analyzer.
- **mdformat** (+ mdformat-frontmatter) — opinionated formatter; useful in a
  pre-commit for vault repos, NOT in the runtime path.
- **markdownlint-cli2** — CI lint for user vaults that opt in.
- No mature Python lib understands Obsidian wikilinks/embeds — our own
  `frontmatter.py` + regex conventions remain the source of truth; this is a
  defensible moat, keep it small and tested.

**Adopt:** nothing in core. Offer mdformat/markdownlint as a documented
pre-commit recipe for Git-synced vaults.

## 3. HTML → Markdown / web capture

- **[trafilatura](https://trafilatura.readthedocs.io/)** — the clear pick:
  boilerplate removal + metadata + Markdown output, MIT, actively maintained
  (see [Glukhov overview](https://www.glukhov.org/documentation-tools/markdown/convert-html-to-markdown-in-python/),
  [Reeve 2024 eval](https://www.osti.gov/servlets/purl/2429881)).
- readability-lxml / markdownify — smaller, worse extraction quality; fallback only.
- [SingleFile](https://github.com/gildas-lormeau/SingleFile) — browser-side
  full-fidelity capture; complements, not competes (user-driven clipping).

**Adopt:** trafilatura as optional extra powering a future `do.clip`
(URL → clean note into `50_Resources` with proper frontmatter + `author: ai`).
This is the most-requested missing workflow.

## 4. Obsidian-specific tooling & plugins

Obsidian's native **Bases** (v1.9+, 2025) now covers most Dataview use cases —
DeepOrbit already ships `.base` files; stay native-first
([reference setup](https://shilu.ai/repos/agricidaniel/claude-obsidian)).

| Plugin | Verdict | Why |
|---|---|---|
| Dataview | **skip** | Bases covers dashboards; Dataview adds a second query language to learn/maintain |
| Tasks | optional | Nice task UI; our tasks stay portable Markdown with `^do-*` IDs either way |
| Templater | optional | Our templates use `{{date}}` tokens the agent fills; Templater helps manual note creation |
| Excalidraw | optional | Visual thinking; files live in-vault, no conflict |
| Smart Connections / Copilot | **skip** | LLM-inside-Obsidian duplicates the agent-runtime architecture and couples to providers |
| Linter | optional | YAML hygiene for hand-edited vaults |
| [Obsidian CLI](https://github.com/Yakitrak/obsidian-cli) / kepano's | adopt (already) | Our `do.obsidian-open` fallback chain uses it |

### Community AI-note repos worth tracking (GitHub/X/小红书 scan, 2026-07)

- **[kepano/obsidian-skills](https://github.com/kepano/obsidian-skills)** —
  Obsidian CEO Steph Ango's official Agent Skills (Jan 2026): small, carefully
  written skills teaching agents Obsidian CLI, Markdown, Bases, JSON Canvas
  ([analysis](https://www.aiwithmo.com/blog/steph-ango-obsidian-skills),
  [dsebastien](https://www.dsebastien.net/obsidian-ai-skills-by-steph-ango/)).
  **Action:** align our `do.*` conventions with it where they overlap
  (Bases/Canvas handling) — it's becoming the de-facto standard surface.
- **[AgriciDaniel/claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian)**
  (~9.5k★) — self-organizing second brain; good UX ideas, but monolithic and
  agent-locked. Watch, don't import.
- **[dxxx/claude-obsidian-memory](https://github.com/dxxx/claude-obsidian-memory)**
  — Karpathy-style LLM-wiki pattern (`/wiki /save /autoresearch`); closest
  analog to our dream pass. Borrow the "promote conversation → wiki" trigger,
  keep our deterministic lifecycle core.
- **[memos](https://github.com/usememos/memos)** — the successful open-source
  flomo; proves quick-capture demand. Our answer is inbox + mobile capture
  recipes, not a server.
- 小红书/中文圈: mostly closed apps (闪念贝壳等 voice-note AI tools) and
  config lists ([夜雨聆风](https://www.yeyulingfeng.com/222057.html)); nothing
  to adopt, but voice-capture → inbox is a workflow gap worth a recipe.

## 5. DeepOrbit's own Obsidian plugin

Community gap confirmed: kepano's skills assume an agent; claude-obsidian
assumes Claude. Nobody ships a *thin* plugin that surfaces an external CLI's
deterministic state inside Obsidian. **`plugin/` in this repo now does exactly
that**: Work Status sidebar (active/paused/done/archived), lifecycle commands
(pause/resume/done/archive with the same no-overwrite semantics as the Python
core), author display. No LLM calls, no provider keys — it reads and writes
the same plain Markdown. Publish path: community plugin submission after
dogfooding.

## Decision table

| Adopt now | Evaluate later | Skip |
|---|---|---|
| Docling (optional extra, PDF) | MinerU (GPU-heavy academic) | Dataview (Bases suffices) |
| trafilatura (optional extra, web clip) | Marker (GPL + heavy deps) | Smart Connections / Copilot (duplicates agent runtime) |
| Own Obsidian plugin (`plugin/`) | GROBID (if citation graphs needed) | memos-style server (scope creep) |
| Align with kepano/obsidian-skills | SingleFile handoff recipe | Streak/gamification plugins |
