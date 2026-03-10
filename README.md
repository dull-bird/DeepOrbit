# DeepOrbit

![DeepOrbit Banner](deeporbit.png)

> **An AI-agent system that bridges LLMs with Obsidian to automate deep research and personal knowledge management.**

[**中文文档**](README_CN.md)

DeepOrbit turns your [Obsidian](https://obsidian.md/) vault into an AI-powered research engine. It uses specialized agent skills (via Gemini CLI / Claude Code) to automate deep research, paper translation, content curation, and vault maintenance — so you can focus on thinking, not filing.

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
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) or [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | ✅ Yes | Agent runtime |
| `xelatex` | Optional | For `/do:arxiv-translator` |
| `playwright` | Optional | For `/do:notebooklm` |

### Setup (3 steps)

```bash
# 1. Clone the repository
git clone https://github.com/dull-bird/DeepOrbit.git

# 2. Run init in your Obsidian vault
# Windows (PowerShell):
& "$env:USERPROFILE\.gemini\extensions\deeporbit\scripts\init_deeporbit_prompt.ps1" "C:\path\to\your\vault"

# macOS/Linux (Bash):
bash ~/.gemini/extensions/deeporbit/scripts/init_deeporbit_prompt.sh ~/path/to/your/vault

# 3. Reload in Gemini CLI
/memory refresh
```

The init script will:
- Copy `DeepOrbitPrompt.md` and `deeporbit.json` into your vault
- Create all vault folders (see structure below)
- Inject `DeepOrbitPrompt.md` into `.gemini/settings.json`

### Language Configuration

Edit `deeporbit.json` in your vault root to set the AI's interaction language:

```json
{ "language": "zh-CN" }
```

> **Note:** Folder paths always stay in English for stability. Only the AI's responses and generated note content follow this setting.

---

## Vault Structure

```mermaid
graph TD
    V["📦 Your Obsidian Vault"] --> A["00_Inbox<br/><i>Quick captures</i>"]
    V --> B["10_Diary<br/><i>Daily logs</i>"]
    V --> C["20_Projects<br/><i>Active projects</i>"]
    V --> D["30_Research<br/><i>Deep dives</i>"]
    V --> E["40_Wiki<br/><i>Atomic concepts</i>"]
    V --> F["50_Resources<br/><i>Newsletters, Product Launches, News</i>"]
    V --> G["60_Notes<br/><i>Summaries & captures</i>"]
    V --> H["90_Plans<br/><i>Execution plans</i>"]
    V --> I["99_System<br/><i>Templates, Prompts, Archive</i>"]

    style V fill:#1a1a2e,stroke:#16213e,color:#e0e0e0
    style A fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style B fill:#0f3460,stroke:#16213e,color:#e0e0e0
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

DeepOrbit ships with **23 pre-configured AI skills**. Invoke them with `/do:<skill-name>`.

```mermaid
mindmap
  root((DeepOrbit Skills))
    🧠 Daily & Planning
      /do:daily
      /do:kickoff
      /do:brainstorm
      /do:ask
    🔬 Research & Knowledge
      /do:research
      /do:parse-knowledge
      /do:note-summary
      /do:recap
    📰 Content Curation
      /do:ai-newsletters
      /do:ai-products
      /do:ai-research-digest
    📚 Academic Tools
      /do:arxiv-translator
      /do:notebooklm
    📄 Document Processing
      /do:pdf-to-markdown
      /do:translate-markdown
    🔧 Vault Maintenance
      /do:fix-links
      /do:archive
      /do:organize
    ⚙️ Obsidian Integration
      do.obsidian-markdown
      do.obsidian-bases
      do.json-canvas
```

### Skills Quick Reference

| Command | What it does |
|---------|-------------|
| `/do:daily` | Morning planning: recap yesterday, fetch news, create today's note |
| `/do:kickoff` | Convert an inbox idea into a structured project (two-agent workflow) |
| `/do:research` | Deep dive into a topic → Research notes + Wiki entries (two-agent workflow) |
| `/do:ask` | Quick Q&A without heavy note-taking |
| `/do:brainstorm` | Interactive Socratic brainstorming partner |
| `/do:note-summary` | Fetch a URL/file → structured summary in `60_Notes` |
| `/do:parse-knowledge` | Turn unstructured text into vault-ready Research + Wiki notes |
| `/do:recap` | Periodic recap report of vault activity over a time range |
| `/do:arxiv-translator` | Download arXiv paper → translate LaTeX → compile PDF |
| `/do:notebooklm` | Query Google NotebookLM for source-grounded answers |
| `/do:pdf-to-markdown` | PDF → Markdown with completeness checklist + image extraction |
| `/do:translate-markdown` | Translate Markdown to target language, section-by-section with verification |
| `/do:ai-newsletters` | Daily AI newsletter digest (RSS-based) |
| `/do:ai-products` | AI product launches digest (Product Hunt, HN, GitHub, Techmeme) |
| `/do:ai-research-digest` | AI research digest from Synced/机器之心 |
| `/do:fix-links` | Scan vault for dead wikilinks → auto-generate Wiki notes |
| `/do:archive` | Archive completed projects and processed inbox items |
| `/do:organize` | Deep vault reorganization: fix taxonomy, orphans, metadata |

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
    A["arXiv URL"] --> B["/do:arxiv-translator"]
    B --> C["Download LaTeX source"]
    C --> D["Translate to target language"]
    D --> E["Compile with xelatex"]
    E --> F["Translated PDF ready"]
```

---

## Philosophy

> Everything orbits around you. Keep your knowledge in motion, but let the AI agents do the heavy lifting of parsing, translating, summarizing, and maintaining the structural integrity of your ideas.
