# WhiteList for Research

This is a high signal-to-noise ratio information source list prepared for DeepOrbit Agents (e.g., `/do:research`).
When conducting deep research or searching for professional content, Agents should prioritize using these domains (e.g., `site:xxx.com`) for targeted mining to avoid "information silos" and low-quality SEO noise.

## 1. Medicine & Life Sciences
When the research topic involves disease mechanisms, clinical protocols, or frontier biology, you **must** search within these high-authority databases and journals, and maintain a strictly rigorous, evidence-based attitude towards the results.
- **PubMed** (`pubmed.ncbi.nlm.nih.gov`): The world's most authoritative biomedical literature database, the preferred search source for basic medicine and clinical research.
- **Cochrane Library** (`cochranelibrary.com`): Provides the highest quality evidence-based medical evidence from systematic reviews and multi-center analyses.
- **UpToDate** (`uptodate.com`): The preferred basis for clinical decision-making (searching for clinical symptoms and treatment consensus).
- **JAMA Network** (`jamanetwork.com`) / **NEJM** (`nejm.org`) / **The Lancet** (`thelancet.com`): The top three international medical journals.
- **Nature / Science** (`nature.com` / `science.org`): Basic life sciences and frontier breakthroughs.

## 2. Computer Science & General Academia
- **Semantic Scholar** (`semanticscholar.org`): AI-driven academic search engine, prioritized for obtaining papers, citation networks, and TLDR summaries.
- **Papers with Code** (`paperswithcode.com`): Use to find the latest machine learning papers, along with the best open-source code implementations for those papers.
- **arXiv** (`arxiv.org`): Computer science frontier theoretical preprints; an endless stream of new algorithms.

## 3. Software Engineering & Architecture
- **Hacker News** (`news.ycombinator.com`): High-quality tech community. Often used to search for real evaluations and pitfalls of a technology from senior engineers (use `site:news.ycombinator.com keyword`).
- **InfoQ** (`infoq.com`): Enterprise-oriented architecture case studies and large-scale backend implementation practices.
- **Stack Overflow** (`stackoverflow.com`): Specific code errors and edge case solutions.
- **GitHub** (`github.com`): Open source library Issues (used to search for known bugs in a framework) and Discussions.

## 🚨 Agent Execution Instructions (Prompt Override)
When acting as a DeepOrbit Execution Agent:
1. Please first determine which of the above broad categories the user's research topic primarily belongs to.
2. When performing WebSearch, you must attempt to include multiple relevant **exclusive site domains** in your search queries. For example:
   `site:pubmed.ncbi.nlm.nih.gov "Major Depressive Disorder" biomarker`
   or `site:news.ycombinator.com "React Server Components" critique`
3. For medical research: If verified evidence is **not found** in these authoritative databases, you must include an extremely explicit warning in the final Markdown notes: `> [!WARNING] Lack of high-level evidence-based support, not to be taken as medical advice.`
