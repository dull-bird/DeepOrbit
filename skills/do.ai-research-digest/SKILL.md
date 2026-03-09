---
name: do.ai-research-digest
description: Fetches and intelligently summarizes the latest in-depth AI articles specifically from "Synced (机器之心)".
---

## Target Sources
- **Jiqizhixin (Synced Chinese)**: `https://www.jiqizhixin.com/rss` (Primary)

## Workflow
1.  **Fetching**: Retrieve the latest entries from 机器之心 within the last 24 hours.
    -   **STRICT RULE**: Use ONLY the specified RSS source. **DO NOT** use Google Search or other search engines to find news if the fetch fails.
2.  **Filtering**: Focus on core research breakthroughs, industry movements, and technical deep dives.
3.  **Summary Generation**:
    -   Use "one-sentence core + 3 technical highlights" format.
    -   All summaries must be in **Chinese**.
    -   Must preserve original Markdown links.

## Error Handling
- If the RSS feed is inaccessible, report the specific error to the user. Do not attempt to "hallucinate" or search for alternative news via general web search.

## Output Template
```markdown
- [文章标题](URL)
  - **核心**: 一句话总结研究/动态的核心价值。
  - **技术亮点**:
    - 亮点1
    - 亮点2
```

## Rules

- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**

