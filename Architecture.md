# DeepOrbit Architecture & Workflows

This document visualizes the core architecture and specialized workflows of **DeepOrbit**, an agent-driven Digital Research Assistant built on top of Obsidian and Gemini CLI / Claude Code.

## 1. Overall System Architecture: DeepOrbit Engine

This diagram illustrates how raw inputs (URLs, Papers, PDFs, Ideas) are ingested by AI Agents, processed through specialized skill packs, and finally structured into the Obsidian local vault.

```mermaid
graph TD
    %% Input Sources
    subgraph Input_Sources [External Inputs]
        Arxiv[arXiv Links/IDs]
        PDF[Local/Remote PDFs]
        URL[Web URLs/Articles]
        News[Newsletters/RSS]
        Idea[Raw Thoughts/Inbox]
    end

    %% Agent Processing Engine
    subgraph Agent_Engine [DeepOrbit Agent Engine]
        direction TB
        CLI{Gemini CLI / Claude Code}
        
        subgraph Academic_Pack [🧠 Academic & Research Pack]
            P_Arxiv["/arxiv-translator"]
            P_Marker["/marker-pdf"]
            P_Translate["/translate-pdf"]
            P_NLM["/notebooklm"]
        end
        
        subgraph Curation_Pack [🕸️ Maintenance & Curation Pack]
            C_Summary["/note-summary"]
            C_Fix["/fix-links"]
            C_Digest["/ai-research-digest</br>/ai-newsletters</br>/ai-products"]
        end
        
        subgraph Core_Pack [⚙️ Core Workflows]
            W_Kickoff["/kickoff"]
            W_Research["/research"]
            W_Parse["/parse-knowledge"]
            W_SMD["/start-my-day"]
        end

        CLI --> Academic_Pack & Curation_Pack & Core_Pack
    end

    %% Obsidian Vault Storage
    subgraph Obsidian_Vault [Obsidian Vault Storage]
        direction LR
        V_Notes[60_笔记]
        V_Wiki[40_知识库]
        V_Proj[20_项目]
        V_Res[50_资源]
        V_Daily[10_日记]
    end

    %% Connections
    Arxiv --> P_Arxiv
    PDF --> P_Marker & P_Translate
    URL --> C_Summary
    News --> C_Digest
    Idea --> W_Kickoff & W_Research

    Academic_Pack -->|Translated/Parsed Markdown| V_Notes & V_Res
    C_Summary -->|Structured Summary| V_Notes
    C_Fix -->|1st Principle Notes| V_Wiki
    C_Digest -->|Daily Digests| V_Res
    Core_Pack --> V_Proj & V_Wiki & V_Daily
    
    P_NLM -.->|RAG Queries| Obsidian_Vault
```

---

## 2. Detailed Workflows: Academic & Research

### 🎓 `/arxiv-translator` & `/marker-pdf`
DeepOrbit automates the heavy lifting of parsing and translating complex academic papers.

```mermaid
graph LR
    Input[arXiv URL / Local PDF] --> Router{Format Check}
    
    Router -- arXiv Source --> ArxivAgent["/arxiv-translator"]
    ArxivAgent --> DL[Download LaTeX]
    DL --> Trans[LLM Translation]
    Trans --> Compile[xeLaTeX Compile]
    Compile --> Out_PDF[Chinese PDF]
    
    Router -- PDF File --> MarkerAgent["/marker-pdf"]
    MarkerAgent --> OCR[marker_single OCR]
    OCR --> Markdown[Preserve Math/Layout]
    Markdown --> Out_MD[Structured Markdown]
    
    Out_PDF & Out_MD --> Vault[Save to 50_资源 / 60_笔记]
```

---

## 3. Detailed Workflows: Knowledge Maintenance

### 🔗 `/fix-links` (Ghost Link Fixer)
This skill ensures your Obsidian Wiki never has dead ends by automatically generating content based on first principles.

```mermaid
graph TD
    Scan[Scan Vault for Ghost Links] --> Identify{Missing Entities Found?}
    Identify -- Yes --> Agent["/fix-links"]
    Identify -- No --> End[Done]
    
    Agent --> Prompt[LLM: 1st Principle Reasoning]
    Prompt --> Gen[Generate Structured Wiki Note]
    Gen --> Classify[Auto-classification]
    Classify --> Save[Save to 40_知识库]
```

### 📰 Content Curation Pipelines
Automated curation of industry news and product launches.

```mermaid
graph LR
    Sources[Product Hunt / HN / Newsletters] --> Agent["/ai-newsletters</br>/ai-products"]
    Agent --> Fetch[Fetch Full Content]
    Fetch --> Dedup[Smart Deduplication]
    Dedup --> Rank[Ranking & Summarization]
    Rank --> Digest[Generate Daily Digest]
    Digest --> Vault[Save to 50_资源]
```
