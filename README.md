# DeepOrbit

![DeepOrbit Banner](deeporbit.png)


> Not just Personal Knowledge Management. A fully automated, Agent-driven Digital Research Assistant.

DeepOrbit is a highly customized, agent-driven Personal Knowledge Management (PKM) and Research Assistant system.

🙏 **Acknowledgments**: DeepOrbit is deeply inspired by and built upon the core philosophy and foundational workflows of [OrbitOS by MarsWang42](https://github.com/MarsWang42/OrbitOS). We extend our sincere gratitude for their innovative approach to vault structure and agent-driven workflows.

While traditional PKM systems focus on manual knowledge entry and linking, **DeepOrbit** is supercharged with specialized AI agents (via Gemini CLI / Claude Code) that automate deep research, literature translation, content curation, and structural maintenance.


## 🗺️ Architecture & Workflows

Curious about how the DeepOrbit Agent Engine works under the hood? 
Check out our **[Architecture & Workflows Documentation](Architecture.md)** for detailed mermaid diagrams illustrating the system architecture, academic translation pipelines, and automated knowledge maintenance loops.

## Core Features & Skill Packs

DeepOrbit comes with a powerful set of pre-configured Agent Skills designed for hard-core researchers, developers, and information curators.

### 🧠 Academic & Research Pack
- **`arxiv-translator`**: Automatically fetches LaTeX sources from arXiv, translates papers to your target language (default: Chinese) preserving formulas, and compiles them to PDF using `xelatex`.
- **`marker-pdf`**: High-fidelity PDF to Markdown conversion (powered by `marker`), specifically tuned for academic papers with complex mathematical notations.
- **`translate-pdf`**: Translates PDF documents while perfectly preserving the original layout, structure, colors, and styling.
- **`notebooklm`**: Queries your Google NotebookLM notebooks via browser automation for source-grounded, hallucination-free, citation-backed answers.

### 🕸️ Knowledge Maintenance & Curation
- **`note-summary`**: Automatically fetches full text from URLs or local files, structures the content, classifies it, and archives it into your knowledge base.
- **`ghost-link-fixer`**: Scans your vault for "ghost" wikilinks (links to non-existent files) and auto-generates deep, first-principle Wiki notes to fill the gaps.
- **`ai-research-digest` / `ai-newsletters` / `ai-products`**: Automated pipelines that curate, deduplicate, and summarize the latest AI research, product launches, and industry newsletters into daily digests.

### ⚙️ Core Workflows (Inherited from OrbitOS)
- **`/kickoff`**: Instantly convert an inbox idea into a structured active Project.
- **`/start-my-day`**: A guided morning planning workflow.
- **`/research`**: Deep dive into any topic with a two-agent architecture that outputs structured Areas and Wiki entries.
- **`/parse-knowledge`**: Consolidates unstructured text blobs into your vault's structural framework.

## Installation & Setup

1. **Prerequisites**: 
   - Gemini CLI or Claude Code.
   - Obsidian (for vault management).
   - Some skills require additional local tools (e.g., `xelatex` for `arxiv-translator`, `playwright` for `notebooklm`, `marker` for `marker-pdf`).
2. **Clone the repository**:
   ```bash
   git clone https://github.com/dull-bird/DeepOrbit.git
   ```
3. **Load Skills**:
   In your CLI configuration file (`AGENTS.md` or `.clauderc`), point the skill locations to the cloned `skills` directory.
   
## Philosophy

Everything orbits around you. Keep your knowledge in motion, but let the AI agents do the heavy lifting of parsing, translating, summarizing, and fixing.
