---
name: ai-newsletters
description: Curate AI newsletter content with smart deduplication and ranking. Use when user invokes /ai-newsletters or when /start-my-day needs newsletter content.
---
# AI Newsletter Curation

Fetch, deduplicate, and rank AI newsletter content into a daily digest.

## RSS Sources
- **机器之心**: `https://www.jiqizhixin.com/rss`
- **TLDR AI**: `https://bullrich.dev/tldr-rss/ai.rss`
- **The Rundown AI**: `https://rss.beehiiv.com/feeds/2R3C6Bt5wj.xml`

## Workflow

1. **Fetch feeds**: Use shell command `curl` on both RSS URLs. Extract title, link, pubDate, description for each item. **DO NOT** use Google Search or other search engines to find news if the fetch fails.

2. **Deduplicate**: Merge items with similar titles (80%+ word overlap). Keep longer description, track both sources. **Priority**: Keep Google/Microsoft/Karpathy/机器之心 as primary sources; append media views as secondary references.

3. **Rank items** by:
   - AI relevance (LLM, GPT, Claude, agents, ML keywords)
   - Recency (newer = higher)
   - Novelty (check recent archives, penalize repeats)

4. **Generate digest**: See [TEMPLATE.md](TEMPLATE.md) for format. Include:
   - 精选推荐 (3-5 highest scoring) with content creation angles
   - AI动态 section
   - 生产力工具 section
   - Stats footer

5. **Save files**:
   - `50_资源/Newsletters/YYYY-MM/YYYY-MM-DD-摘要.md` (curated, make sure existence!)
   - `50_资源/Newsletters/YYYY-MM/原始数据/YYYY-MM-DD_机器之心-Raw.md`
   - `50_资源/Newsletters/YYYY-MM/原始数据/YYYY-MM-DD_TLDR-AI-Raw.md`
   - `50_资源/Newsletters/YYYY-MM/原始数据/YYYY-MM-DD_Rundown-AI-Raw.md`

## Output Format

**Manual invocation**: Display full digest with all sections. Make sure all `.md` files are saved.

**From /start-my-day**: Display full digest with all sections. Make sure all `.md` files are saved. Then return a condensed list:
```
**AI 新闻 (5):**
- [标题] - [角度]
...
完整摘要: [[YYYY-MM-DD-摘要]]
```

## Error Handling

- One feed down: Continue with other, note in digest
- Both down: Use yesterday's archive with warning
- Empty feeds: Create minimal digest noting "今日无新内容"
