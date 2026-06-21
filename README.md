# DeepOrbit

![DeepOrbit Banner](deeporbit.png)

> **An AI-agent system that bridges LLMs with Obsidian to automate deep research and personal knowledge management.**

[**中文文档**](README_CN.md)

DeepOrbit turns your [Obsidian](https://obsidian.md/) vault into an AI-powered research engine. It uses portable **Agent Skills** (compatible with Claude Code, Cursor, Codex, Gemini CLI, and any agent that supports the standard) to automate deep research, paper translation, content curation, and vault maintenance — so you can focus on thinking, not filing.

> [!IMPORTANT]
> **Obsidian is required.** DeepOrbit's folder structure, wikilink system, and templates all depend on a local Obsidian vault.

🙏 **Acknowledgments**: DeepOrbit is deeply inspired by [OrbitOS by MarsWang42](https://github.com/MarsWang42/OrbitOS). We extend our sincere gratitude for their innovative approach to vault structure and agent-driven workflows.

---

## How It Works

```mermaid
flowchart TD
    A["🧠 You"] -->|ideas, URLs, PDFs| B["⚙️ DeepOrbit Agent"]
    B -->|selects skill| C["🧩 Skill Pack"]
    C -->|writes notes| D["📂 Obsidian Vault"]
    D -->|wikilinks| A
```

You give DeepOrbit raw inputs — an arXiv link, a PDF, a quick idea, a URL. The Agent Engine routes your request to the right **Skill**, which processes, translates, summarizes, or structures the content and saves it directly into your Obsidian vault with proper metadata and wikilinks.

---

## Quick Start

### Prerequisites

| Tool | Required? | Note |
|------|-----------|------|
| [Obsidian](https://obsidian.md/) | ✅ Yes | Vault management |
| An Agent Skills runtime — [Claude Code](https://docs.anthropic.com/en/docs/claude-code), Cursor, Codex, [Gemini CLI](https://github.com/google-gemini/gemini-cli), etc. | ✅ Yes | Agent runtime |
| [obsidian-skills](https://github.com/kepano/obsidian-skills) | ✅ Yes | Required for native Obsidian formats. If using Gemini CLI, ask the AI to "add https://github.com/kepano/obsidian-skills to my system skills". |
| [ralph](https://github.com/gemini-cli-extensions/ralph) | **Gemini CLI only** | Drives the section-by-section *manifest loop* in `/do:pdf-to-markdown`, `/do:translate-markdown`, `/do:research`. On Claude Code the same loop runs natively via sub-agents (Task tool) or the `/loop` command — no extra install. |
| `xelatex` | **recommended** | For `/do:arxiv-translator`.<br/>- macOS: `brew install --cask mactex-no-gui`<br/>- Windows: [MiKTeX](https://miktex.org/) or [TeX Live](https://www.tug.org/texlive/) |
| `obsidian-cli` | **recommended** | For `do.obsidian-open` to automatically open generated notes.<br/>- See: https://obsidian.md/cli |

### Setup Instructions

DeepOrbit is a standard **Agent Skills** pack. Pick whichever installer matches your agent — all three install the same skills from `skills/`.

#### Method A: `npx skills` (Recommended — works with any agent)

The universal installer. It supports Claude Code, Cursor, Codex, Windsurf, and many others, and symlinks the skills into each tool's directory automatically.

```bash
# In your project (or run with --global for user-wide install)
npx skills add dull-bird/DeepOrbit
```

#### Method B: Claude Code plugin

```text
/plugin marketplace add dull-bird/DeepOrbit
/plugin install deeporbit@deeporbit
```

This registers all 22 `do.*` skills as a Claude Code plugin. Restart or reload skills to activate.

#### Method C: Gemini CLI (compatibility)

```bash
gemini extension install dull-bird/DeepOrbit
```

The `commands/do/*.toml` slash commands keep working for Gemini CLI users.

#### Then: initialize your vault (all methods)

Inject DeepOrbit's core prompt into your Obsidian vault, then activate:

- **macOS/Linux**: `bash scripts/init_deeporbit_prompt.sh ~/path/to/your/vault`
- **Windows**: `& ".\scripts\init_deeporbit_prompt.ps1" "C:\path\to\your\vault"`

Then ask your agent in natural language ("run init", "start research") — it discovers the skills automatically. Gemini CLI users can also run `/do:init ~/path/to/your/vault` followed by `/memory refresh`.

#### Optional: native RAG tools via MCP

`do.rag` and `do.search` shell out to the scripts in `scripts/rag/` by default. If you'd rather call them as native MCP tools (`rag_query`, `rag_search`), the repo ships an optional MCP server — see [`mcp/README.md`](mcp/README.md) and the project-scoped [`.mcp.json`](.mcp.json).

### Language Configuration

Edit `deeporbit.json` in your vault root to set the AI's interaction language:

```json
{ "language": "zh-CN" }
```

> **Note:** Folder paths always stay in English for stability. Only the AI's responses and generated note content follow this setting.

---

## Vault Structure

```mermaid
flowchart LR
    V["📦 Your Obsidian Vault"]
    
    V --- G1["Captured & Active"]
    V --- G2["Knowledge Base"]
    V --- G3["Resources & System"]

    G1 --- A["00_Inbox<br/><i>Quick captures</i>"]
    G1 --- B["10_Diary<br/><i>Daily logs</i>"]
    G1 --- W["15_Writings<br/><i>Creative writing & essays</i>"]
    G1 --- C["20_Projects<br/><i>Active projects</i>"]
    
    G2 --- D["30_Research<br/><i>Deep dives</i>"]
    G2 --- E["40_Wiki<br/><i>Atomic concepts</i>"]
    G2 --- G["60_Notes<br/><i>Summaries & captures</i>"]
    
    G3 --- F["50_Resources<br/><i>Newsletters & Products</i>"]
    G3 --- H["90_Plans<br/><i>Execution plans</i>"]
    G3 --- I["99_System<br/><i>Templates & Prompts</i>"]

    style V fill:#1a1a2e,stroke:#16213e,color:#e0e0e0
    style G1 fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style G2 fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style G3 fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style A fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style B fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style W fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style C fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style D fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style E fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style F fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style G fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style H fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style I fill:#0f3460,stroke:#16213e,color:#e0e0e0
```

---

## Skills Overview

DeepOrbit ships with **22 pre-configured `do.*` skills** (plus optional external [obsidian-skills](https://github.com/kepano/obsidian-skills) for native Obsidian formats), split into two categories:

### 🌐 Universal Skills (Work Anywhere)

These skills work independently — no Obsidian vault required.

```mermaid
mindmap
  root((Universal Skills))
    🧠 Thinking
      /do:ask
      /do:brainstorm
    📚 Academic
      /do:arxiv-translator
    📄 Document Processing
      /do:pdf-to-markdown
      /do:translate-markdown
      /do:translate
    ⚙️ Diagramming
      do.mermaid
```

### 📂 Obsidian Skills (Require Vault)

These skills read from or write to the DeepOrbit vault structure.

```mermaid
mindmap
  root((Obsidian Skills))
    🧠 Daily & Planning
      /do:daily
      /do:kickoff
      /do:write
    🔬 Research & Knowledge
      /do:research
      /do:parse-knowledge
      /do:note-summary
      /do:recap
      /do:rag
      /do:rag-index
      /do:search
     Academic Tools
      /do:arxiv-translator
    📄 Document Processing
      /do:pdf-to-markdown
      /do:translate-markdown
      /do:translate
    🔧 Vault Maintenance
      /do:fix-links
      /do:archive
      /do:organize
      /do:refresh-prompt
    ⚙️ Obsidian Integration
      obsidian-markdown
      obsidian-bases
      json-canvas
      obsidian-cli
      do.obsidian-open
```

### Skills Quick Reference

| Command | What it does |
|---------|-------------|
| `/do:daily` | Morning planning: recap yesterday, fetch news, create today's note |
| `/do:kickoff` | Convert an inbox idea into a structured project (two-agent workflow) |
| `/do:research` | Deep dive into a topic → Research notes + Wiki entries (two-agent workflow) |
| `/do:ask` | Quick Q&A without heavy note-taking |
| `/do:brainstorm` | Interactive Socratic brainstorming partner |
| `/do:rag` | Ask questions using semantic search across your entire vault |
| `/do:rag-index` | Index the Obsidian vault for semantic RAG search |
| `/do:search` | Fast exact keyword or regex string match search across your vault |
| `/do:note-summary` | Auto-fetch URL/file/paper → structured summary + vault archiving |
| `/do:parse-knowledge` | Turn unstructured text into vault-ready Research + Wiki notes |
| `/do:arxiv-translator` | Download arXiv paper → translate LaTeX → compile PDF |
| `/do:pdf-to-markdown` | PDF → Markdown with completeness checklist + image extraction |
| `/do:translate-markdown` | Translate Markdown to target language, section-by-section with verification |
| `/do:translate` | Smartly route translation requests for arXiv or standard PDFs to appropriate skills |
| `/do:organize` | Deep vault reorganization: root hygiene, taxonomy, orphans, metadata |
| `/do:refresh-prompt` | Safely update DeepOrbitPrompt.md with diff comparison + merge options |
| `do.obsidian-open` | Utility to automatically open modified notes in Obsidian via CLI |

---

### 🤖 Multi-Agent Compatibility

DeepOrbit ships as tool-neutral **Agent Skills** (`skills/do.*/SKILL.md`), so any agent that supports the standard discovers and triggers them by description:

*   **Claude Code / Cursor / Codex / Windsurf**: Install via `npx skills add` or the Claude Code plugin. Skills trigger automatically by intent, or you invoke them in natural language ("start research", "summarize this PDF").
*   **Gemini CLI**: In addition to skills, the `commands/do/*.toml` files register native `/do:command` slash commands.

The single source of truth is `skills/`; the per-tool install directories are generated by the installer and are git-ignored.

---

---

## Core Workflow Examples

### 🌅 Morning Routine

```mermaid
flowchart TD
    A["Run /do:daily"] --> B["Review yesterday's diary"]
    B --> C["Knowledge Recap: what changed in 24h?"]
    C --> D["Set today's goals"]
    D --> E["Fetch news from ## News sources"]
    E --> F["Generate summaries in 50_Resources/Newsletters/"]
    F --> G["Create today's diary: 10_Diary/YYYY-MM-DD.md"]
```

### 💡 Idea → Project

```mermaid
flowchart TD
    A["Idea in 00_Inbox"] -->|"/do:kickoff"| B["Planning Agent<br/>creates plan in 90_Plans/"]
    B -->|"User reviews"| C["Execution Agent<br/>creates project in 20_Projects/"]
    C --> D["Inbox item archived to 99_System/Archive/"]
```

### 📄 Academic Paper Pipeline

```mermaid
flowchart TD
    A["Input: arXiv URL / Local PDF"] --> B["/do:translate"]
    B --> C{Detect Type}
    C -->|arXiv| D["/do:arxiv-translator"]
    D --> E["Download & Translate LaTeX"]
    E --> F["Compile to PDF"]
    C -->|PDF| G["/do:pdf-to-markdown"]
    G --> H["/do:translate-markdown"]
    F & H --> I["Save to 60_Notes/papers/"]
```

### 📝 Automated Summary & Archiving

```mermaid
flowchart TD
    A["Input: URL / PDF / Title"] --> B["/do:note-summary"]
    B --> C["Phase 0: Fetch Full Content"]
    C --> D["Phase 1: Screening & Outline"]
    D --> E{Depth Mode?}
    E -->|Quick| I["Phase 4: Quality Verification"]
    E -->|Standard / Deep| F["Phase 2: Section Summaries"]
    F --> G{Is Deep Mode?}
    G -->|Yes| H["Phase 3: Critical Analysis"]
    G -->|No| I
    H --> I
    I --> J["Phase 5: Save to 60_Notes & Wiki Links"]
```

---

## Philosophy

> Everything orbits around you. Keep your knowledge in motion, but let the AI agents do the heavy lifting of parsing, translating, summarizing, and maintaining the structural integrity of your ideas.
lating, summarizing, and maintaining the structural integrity of your ideas.
