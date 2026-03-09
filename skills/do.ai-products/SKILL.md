---
name: do.ai-products
description: Curate AI product launches from Product Hunt, Hacker News, GitHub, and Techmeme. Use when user invokes /do:ai-products or when /do:daily needs product launches.
---
# AI Product Discovery

Fetch, deduplicate, and rank AI product launches from multiple sources.

## Sources

| Source | URL | Notes |
|--------|-----|-------|
| Product Hunt | `https://www.producthunt.com/feed` | Filter for AI-related |
| Hacker News | `https://hn.algolia.com/api/v1/search?tags=show_hn&numericFilters=created_at_i>TIMESTAMP` | Show HN posts, 24h window |
| GitHub Trending | `https://mshibanami.github.io/GitHubTrendingRSS/daily/python.xml` | Python repos |
| Techmeme | `https://techmeme.com/river` | Product announcements |

## Workflow

1.  **Check cache**: Look for `50_Resources/Product Launches/YYYY-MM/YYYY-MM-DD-Digest.md`. If exists with today's date, return cached.

2.  **Fetch sources**: Use shell command `curl` on each. Extract product name, URL, description, and engagement metrics (votes/points/stars).

3.  **Filter**: Keep only AI-related products (keywords: AI, ML, LLM, GPT, Claude, automation, agent, model).

4.  **Deduplicate**: Same product across sources = merge. Keep best description, combine metrics, track all sources.

5.  **Rank by**:
    - AI relevance
    - Engagement (normalize: PH votes/500, HN points/100, GH stars/1000)
    - Content potential (tutorial-friendly, review-worthy, open source bonus)
    - Recency and novelty

6.  **Generate digest**: See [TEMPLATE.md](TEMPLATE.md). Sections:
    - Featured Recommendations (3-5) with content angles
    - LLM and AI Models
    - Developer Tools
    - Productivity and Automation
    - Open Source Highlights

7.  **Save files**:
    - `50_Resources/Product Launches/YYYY-MM/YYYY-MM-DD-Digest.md` (ensure existence!)
    - `50_Resources/Product Launches/YYYY-MM/Raw Data/YYYY-MM-DD_ProductHunt-Raw.md`
    - `50_Resources/Product Launches/YYYY-MM/Raw Data/YYYY-MM-DD_HackerNews-Raw.md`
    - `50_Resources/Product Launches/YYYY-MM/Raw Data/YYYY-MM-DD_GitHub-Raw.md`

## Output Format

**Manual invocation**: Full digest with all sections. Make sure all `.md` files are saved.

**From /do:daily**: Display full digest with all sections. Make sure all `.md` files are saved. Then return a condensed list:
```
**Product Launches (5):**
- [Product Name] - [Content Angle] - [Key Metrics]
...
Full Digest: [[YYYY-MM-DD-Digest]]
```

## Error Handling

- Source down: Continue with others, note in digest
- <2 sources available: Fall back to yesterday's archive
- Empty results: Create minimal digest noting "No new AI products today"

## Content Angle Logic

- High engagement + tutorial-friendly: "Tutorial Opportunity"
- Novel + early stage: "Early Bird Advantage"
- Open source + complex: "In-depth Analysis"
- SaaS + practical: "Tool Review"
- Similar to existing: "Comparison vs [Competitor]"

## Rules

- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**

