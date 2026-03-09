---
name: do.ai-newsletters
description: Curate AI newsletter content with smart deduplication and ranking. Use when user invokes /do:ai-newsletters or when /do:daily needs newsletter content.
---

# AI Newsletter Curation

Fetch, deduplicate, and rank AI newsletter content into a daily digest.

## RSS Sources

- **机器之心**: `https://www.jiqizhixin.com/rss`
- **TLDR AI**: `https://bullrich.dev/tldr-rss/ai.rss`
- **The Rundown AI**: `https://rss.beehiiv.com/feeds/2R3C6Bt5wj.xml`

## Workflow

1.  **Fetch feeds**: Use shell command `curl` on both RSS URLs. Extract title, link, pubDate, description for each item. **DO NOT** use Google Search or other search engines to find news if the fetch fails.
2.  **Deduplicate**: Merge items with similar titles (80%+ word overlap). Keep longer description, track both sources. **Priority**: Keep Google/Microsoft/Karpathy/机器之心 as primary sources; append media views as secondary references.
3.  **Rank items** by:
    - AI relevance (LLM, GPT, Claude, agents, ML keywords)
    - Recency (newer = higher)
    - Novelty (check recent archives, penalize repeats)

4.  **Generate digest**: See [TEMPLATE.md](TEMPLATE.md) for format. Include:
    - Featured Recommendations (3-5 highest scoring) with content creation angles
    - AI Trends section
    - Productivity Tools section
    - Stats footer

5.  **Save files**:
    - `50_Resources/Newsletters/YYYY-MM/YYYY-MM-DD-Summary.md` (curated, ensure existence!)
    - `50_Resources/Newsletters/YYYY-MM/Raw Data/YYYY-MM-DD_机器之心-Raw.md`
    - `50_Resources/Newsletters/YYYY-MM/Raw Data/YYYY-MM-DD_TLDR-AI-Raw.md`
    - `50_Resources/Newsletters/YYYY-MM/Raw Data/YYYY-MM-DD_Rundown-AI-Raw.md`

## Output Format

**Manual invocation**: Display full digest with all sections. Make sure all `.md` files are saved.

**From /do:daily**: Display full digest with all sections. Make sure all `.md` files are saved. Then return a condensed list:

```
**AI News (5):**
- [Title] - [Angle]
...
Full Digest: [[YYYY-MM-DD-Summary]]
```

## Error Handling

- One feed down: Continue with other, note in digest
- Both down: Use yesterday's archive with warning
- Empty feeds: Create minimal digest noting "No new content today"

## Rules

- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**

