---
type: recipe
name: Daily News
description: Fetch the day's news sources and distill them into per-source summaries under 50_Resources/Newsletters
schedule: daily
author: ai
---

# Daily News

Run every morning (schedule with `deeporbit cron add daily-news "Run recipe Daily News" --every daily`).

1. note: Ensure today's daily note exists in 10_Diary with a `## News sources` section; if it is missing, copy the list from `99_System/Templates/News_sources_default.md`.
2. cli: bash scripts/fetch_news_sources.sh "10_Diary/<today>.md" "50_Resources/Newsletters/<today>/raw"
3. skill: do.daily — run ONLY the "# 4. News" section: verify each raw file, then write one `50_Resources/Newsletters/<today>/<label>.md` summary per source with direct article links. Never hallucinate fetch failures.
4. note: Append a 3-5 line "今日要闻" digest at the top of today's daily note linking to the per-source summaries, then run `deeporbit --vault . index` so the summaries are searchable.

Step 2 resolves the fetch script the way do.daily does: repo checkout `scripts/fetch_news_sources.sh`, the vault runtime bundle, or the Gemini extension folder — locate it with glob before executing. On Windows use the `.ps1` variant.

Handoff to an agent CLI: `deeporbit --vault . cron run-due --agent` wraps this recipe in the configured agent's command line.
